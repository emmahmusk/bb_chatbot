import re
import logging

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Max, Min
from django.utils import timezone
from django.views.generic import TemplateView
from openai import OpenAIError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chatbot.models import ChatMessage, Conversation, MarketDocument
from .serializers import ChatRequestSerializer, SyncRequestSerializer
from .services.indexer import sync_market_index
from .services.market_api import MarketAPIError
from .services.openai_client import generate_answer, resolve_followup
from .services.retrieval import build_context, retrieve_markets


REFERENCE_WITHOUT_CONTEXT_RE = re.compile(
    r"\b(?:it|that|this|those|them|same|other one|previous one)\b|^\s*(?:what|how)\s+about\b",
    re.I,
)
logger = logging.getLogger(__name__)


def _plain_answer(structured):
    return "\n\n".join(
        [structured["summary"]]
        + [
            section["heading"]
            + "\n"
            + "\n".join(
                f"- {point['label']}: {point['text']}" for point in section["points"]
            )
            for section in structured["sections"]
        ]
        + [structured["disclaimer"]]
    )


def _clarification_answer(question):
    return {
        "summary": "I need one detail before I can answer accurately.",
        "sections": [
            {
                "heading": "Quick clarification",
                "points": [
                    {
                        "label": "Please confirm",
                        "text": question,
                        "style": "caution",
                    }
                ],
            }
        ],
        "disclaimer": "Educational only - not financial advice.",
    }


def _message_payload(message):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "structured_answer": message.structured_answer,
        "sources": message.sources,
        "needs_clarification": message.needs_clarification,
        "created_at": message.created_at.isoformat(),
    }


def _conversation_history(conversation):
    limit = max(2, settings.CONVERSATION_HISTORY_LIMIT)
    messages = list(conversation.messages.order_by("-created_at", "-id")[:limit])
    messages.reverse()
    return [{"role": message.role, "content": message.content} for message in messages]


def _contextual_fallback_query(message, history):
    """Keep retrieval usable when a follow-up resolver is unnecessary or unavailable."""
    user_turns = [item["content"] for item in history if item["role"] == "user"][-4:]
    parts = user_turns + [message]
    return "Conversation context: " + " | ".join(part.strip() for part in parts if part.strip())


def _save_exchange(conversation, user_text, assistant_text, structured, sources, needs_clarification):
    with transaction.atomic():
        ChatMessage.objects.create(
            conversation=conversation,
            role="user",
            content=user_text,
        )
        ChatMessage.objects.create(
            conversation=conversation,
            role="assistant",
            content=assistant_text,
            structured_answer=structured,
            sources=sources,
            needs_clarification=needs_clarification,
        )
        updates = {"updated_at": timezone.now()}
        if not conversation.title:
            updates["title"] = user_text.strip()[:157]
        Conversation.objects.filter(pk=conversation.pk).update(**updates)
        for key, value in updates.items():
            setattr(conversation, key, value)


class ChatPageView(TemplateView):
    template_name = "chatbot/index.html"


class OddsComparisonPageView(TemplateView):
    template_name = "chatbot/odds_comparison.html"


class AdminSportsbookPageView(TemplateView):
    template_name = "chatbot/admin_sportsbook.html"


class AdminMonitorPageView(TemplateView):
    template_name = "chatbot/admin_monitor.html"


class HealthView(APIView):
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        indexed_markets = MarketDocument.objects.count()
        indexed_symbols = MarketDocument.objects.values("symbol").distinct().count()
        expiry_range = MarketDocument.objects.aggregate(
            earliest_expiry=Min("expiry_date"),
            latest_expiry=Max("expiry_date"),
        )
        return Response({
            "status": "ok",
            "indexed_markets": indexed_markets,
            "indexed_symbols": indexed_symbols,
            "index_complete": indexed_markets > indexed_symbols > 0,
            "earliest_expiry": (
                expiry_range["earliest_expiry"].isoformat()
                if expiry_range["earliest_expiry"] else None
            ),
            "latest_expiry": (
                expiry_range["latest_expiry"].isoformat()
                if expiry_range["latest_expiry"] else None
            ),
        })


class MarketSyncView(APIView):
    def post(self, request):
        serializer = SyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = sync_market_index(**serializer.validated_data)
        except MarketAPIError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(result)


class ConversationDetailView(APIView):
    def get(self, request, conversation_id):
        conversation = Conversation.objects.filter(pk=conversation_id).first()
        if not conversation:
            return Response({"error": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        messages = list(conversation.messages.order_by("-created_at", "-id")[:100])
        messages.reverse()
        return Response({
            "conversation_id": str(conversation.id),
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": [_message_payload(message) for message in messages],
        })


class ChatView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        conversation_id = data.get("conversation_id")
        if conversation_id:
            conversation = Conversation.objects.filter(pk=conversation_id).first()
            if not conversation:
                return Response(
                    {"error": "Conversation not found. Start a new chat and try again."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            conversation = Conversation.objects.create()

        history = _conversation_history(conversation)
        if not history and data.get("history"):
            history = data["history"][-settings.CONVERSATION_HISTORY_LIMIT:]

        resolution = {
            "standalone_query": data["message"],
            "needs_clarification": False,
            "clarification_question": "",
        }
        latest_message = conversation.messages.order_by("-created_at", "-id").first()
        answering_clarification = bool(
            latest_message
            and latest_message.role == "assistant"
            and latest_message.needs_clarification
        )
        should_resolve = (
            not answering_clarification
            and (bool(history) or bool(REFERENCE_WITHOUT_CONTEXT_RE.search(data["message"])))
        )
        if answering_clarification:
            resolution["standalone_query"] = _contextual_fallback_query(data["message"], history)
        elif should_resolve:
            try:
                resolution = resolve_followup(data["message"], history)
            except (OpenAIError, RuntimeError):
                logger.exception("Follow-up resolution failed; using conversation-history fallback")
                if history:
                    resolution["standalone_query"] = _contextual_fallback_query(data["message"], history)
                else:
                    resolution = {
                        "standalone_query": data["message"],
                        "needs_clarification": True,
                        "clarification_question": "Which stock, market, or earlier scenario do you mean?",
                    }

        if resolution["needs_clarification"]:
            question = resolution["clarification_question"] or "Which stock or market do you mean?"
            structured = _clarification_answer(question)
            answer = _plain_answer(structured)
            _save_exchange(
                conversation,
                data["message"],
                answer,
                structured,
                [],
                True,
            )
            return Response({
                "conversation_id": str(conversation.id),
                "answer": answer,
                "structured_answer": structured,
                "needs_clarification": True,
                "resolved_query": resolution["standalone_query"],
                "as_of": timezone.now().isoformat(),
                "model": settings.OPENAI_CHAT_MODEL,
                "sources": [],
            })

        if not MarketDocument.objects.exists() and settings.AUTO_SYNC_EMPTY_INDEX:
            try:
                sync_market_index()
            except MarketAPIError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        if not MarketDocument.objects.exists():
            return Response(
                {"error": "The market index is empty. Run POST /api/markets/sync/ first."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        top_k = data.get("top_k", settings.RAG_TOP_K)
        resolved_query = resolution["standalone_query"] or data["message"]
        matches = retrieve_markets(resolved_query, top_k)
        context, citations = build_context(resolved_query, matches)
        try:
            structured = generate_answer(resolved_query, history, context)
        except OpenAIError:
            logger.exception("OpenAI answer generation failed for conversation %s", conversation.id)
            return Response(
                {"error": "The market assistant is temporarily unavailable. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except RuntimeError:
            logger.exception("Structured answer generation failed for conversation %s", conversation.id)
            return Response(
                {"error": "The assistant could not prepare a complete answer. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        answer = _plain_answer(structured)
        _save_exchange(
            conversation,
            data["message"],
            answer,
            structured,
            citations,
            False,
        )
        return Response({
            "conversation_id": str(conversation.id),
            "answer": answer,
            "structured_answer": structured,
            "needs_clarification": False,
            "resolved_query": resolved_query,
            "as_of": timezone.now().isoformat(),
            "model": settings.OPENAI_CHAT_MODEL,
            "sources": citations,
            "disclaimer": "Market probabilities and model output are estimates, not guaranteed returns or financial advice.",
        })
