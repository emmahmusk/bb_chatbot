from django.conf import settings
from django.db import connection
from django.db.models import Max, Min
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from openai import OpenAIError

from chatbot.models import MarketDocument
from .serializers import ChatRequestSerializer, SyncRequestSerializer
from .services.indexer import sync_market_index
from .services.market_api import MarketAPIError
from .services.openai_client import generate_answer
from .services.retrieval import build_context, retrieve_markets


class ChatPageView(TemplateView):
    template_name = "chatbot/index.html"


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


class ChatView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
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
        matches = retrieve_markets(data["message"], top_k)
        context, citations = build_context(data["message"], matches)
        try:
            structured = generate_answer(data["message"], data.get("history", []), context)
        except OpenAIError:
            return Response(
                {"error": "The market assistant is temporarily unavailable. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except RuntimeError:
            return Response(
                {"error": "The assistant could not prepare a complete answer. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        answer = "\n\n".join(
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
        return Response({
            "answer": answer,
            "structured_answer": structured,
            "as_of": timezone.now().isoformat(),
            "model": settings.OPENAI_CHAT_MODEL,
            "sources": citations,
            "disclaimer": "Market probabilities and model output are estimates, not guaranteed returns or financial advice.",
        })
