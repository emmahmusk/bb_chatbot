from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator
import re
from typing import Literal


def clean_display_text(value):
    value = str(value or "").strip()
    value = re.sub(r"^#{1,6}\s*", "", value)
    value = re.sub(r"^(?:[-*]|\d+[.)])\s+", "", value)
    value = value.replace("**", "").replace("`", "").replace("__", "")
    value = re.sub(r"^\*(.+)\*$", r"\1", value)
    return value


class AnswerPoint(BaseModel):
    label: str = Field(description="Short label such as Over 305, Ownership, or Example")
    text: str = Field(description="Plain-language explanation that follows the label")
    style: Literal["standard", "insight", "calculation", "caution"] = "standard"

    @field_validator("label", "text")
    @classmethod
    def clean_point_text(cls, value):
        return clean_display_text(value)


class AnswerSection(BaseModel):
    heading: str = Field(description="Short plain-text heading without formatting markers")
    points: list[AnswerPoint] = Field(min_length=1, max_length=5)

    @field_validator("heading")
    @classmethod
    def clean_heading(cls, value):
        return clean_display_text(value)


class StructuredAnswer(BaseModel):
    summary: str = Field(description="Direct one- or two-sentence answer")
    sections: list[AnswerSection] = Field(min_length=1, max_length=4)
    disclaimer: Literal["Educational only - not financial advice."]

    @field_validator("summary", "disclaimer", mode="before")
    @classmethod
    def clean_text_fields(cls, value):
        return clean_display_text(value)


class QueryResolution(BaseModel):
    standalone_query: str = Field(
        description="A self-contained market question with relevant prior context resolved"
    )
    needs_clarification: bool
    clarification_question: str = Field(
        description="One concise question when clarification is essential; otherwise an empty string"
    )

    @field_validator("standalone_query", "clarification_question")
    @classmethod
    def clean_resolution_text(cls, value):
        return clean_display_text(value)


def get_openai_client():
    return OpenAI()


def embed_texts(texts):
    if not texts:
        return []
    embeddings = []
    for start in range(0, len(texts), 100):
        response = get_openai_client().embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=texts[start : start + 100],
        )
        embeddings.extend(item.embedding for item in response.data)
    return embeddings


def generate_answer(message, history, context):
    instructions = """You are BullBear Market Assistant, a careful financial education assistant for people
who may have no investing or betting experience.

ACCURACY RULES
- Use only the supplied BullBear context for market-specific facts.
- A market written STOCK > TARGET wins only when the settlement price is strictly greater than TARGET.
  At exactly TARGET, the over wager does not win. Never use exactly TARGET as a winning example.
- Buying shares and placing a wager are different. Shares have a changing resale value and no expiry;
  a wager is all-or-nothing at its stated expiry and gives no ownership.
- If the user gives no wager amount, never use the share price as the stake. Use the supplied $100 example.
- Decimal odds are total return including the original stake. State both total returned and profit.
- Translate probabilities into plain language: near 50% is roughly even or uncertain, 60-69% is a
  moderate lean, and 70% or more is a stronger lean. Probabilities are never guarantees.
- If the requested horizon has no matching expiry, state the actual expiry used.

WRITING RULES
- Return plain text only inside the structured fields. Never include Markdown, HTML, hashtags, asterisks,
  formatting markers, tables, or numbered heading prefixes.
- Put the direct answer in summary. Organize details into short section headings and concise points.
- Every point needs a short label and explanatory text. Use calculation style only for arithmetic,
  insight for the most useful interpretation, caution for material risk, and standard otherwise.
- Define unavoidable terms immediately in everyday language. Prefer all-or-nothing wager over binary.
- Show no more than two short calculations. Round money to 2 decimals and probabilities to percentages.
- Lead with what the numbers mean. Keep the entire answer focused and normally under 300 words.
- Do not repeat the question, label facts as quoted context, or offer a menu of follow-up tasks.
- Set disclaimer to exactly: Educational only - not financial advice.
- If context is insufficient, say so plainly instead of guessing."""
    conversation = [
        {"role": item["role"], "content": item["content"]}
        for item in history[-8:]
    ]
    conversation.append(
        {
            "role": "user",
            "content": f"MARKET CONTEXT\n{context}\n\nUSER QUESTION\n{message}",
        }
    )
    response = get_openai_client().responses.parse(
        model=settings.OPENAI_CHAT_MODEL,
        instructions=instructions,
        input=conversation,
        text_format=StructuredAnswer,
    )
    if not response.output_parsed:
        raise RuntimeError("The model did not return a structured answer.")
    return response.output_parsed.model_dump()


def resolve_followup(message, history):
    instructions = """You resolve user messages in an ongoing BullBear market conversation.
Use the conversation history to turn the newest user message into a self-contained market query.

RULES
- Resolve pronouns and short references such as it, that one, the other stock, same amount, or that expiry.
- Preserve relevant tickers, companies, investment amounts, targets, dates, and the user's intended comparison.
- A later explicit value replaces an earlier value. Never invent a ticker, amount, date, or preference.
- If the history supplies enough context, set needs_clarification to false and produce standalone_query.
- Ask for clarification only when a missing detail would materially change the answer and cannot be inferred.
- Do not ask about optional preferences. Do not ask the user to repeat details already present in history.
- When clarification is needed, ask exactly one short, specific question.
- Return plain text only, without Markdown or HTML."""
    conversation = [
        {"role": item["role"], "content": item["content"]}
        for item in history[-12:]
    ]
    conversation.append({"role": "user", "content": message})
    response = get_openai_client().responses.parse(
        model=settings.OPENAI_CHAT_MODEL,
        instructions=instructions,
        input=conversation,
        text_format=QueryResolution,
    )
    if not response.output_parsed:
        raise RuntimeError("The model did not resolve the follow-up query.")
    return response.output_parsed.model_dump()
