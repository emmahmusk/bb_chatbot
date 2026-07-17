import math
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from chatbot.models import MarketDocument
from .openai_client import embed_texts

TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")
MONEY_RE = re.compile(r"(?:\$|USD\s+)([0-9][0-9,]*(?:\.\d{1,2})?)", re.I)
ACTION_AMOUNT_RE = re.compile(
    r"\b(?:invest|stake|wager|bet|risk|spend)\s+(?:about\s+)?([0-9][0-9,]*(?:\.\d{1,2})?)\b",
    re.I,
)
MONTH_RE = re.compile(r"\b(?:in|over|for)\s+(\d{1,2})\s+months?\b", re.I)


def _cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    denom = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / denom if denom else 0.0


def retrieve_markets(query, top_k):
    query_embedding = embed_texts([query])[0]
    docs = list(MarketDocument.objects.all())
    upper_query = query.upper()
    scored = []
    for doc in docs:
        score = _cosine(query_embedding, doc.embedding)
        if doc.symbol and re.search(rf"\b{re.escape(doc.symbol)}\b", upper_query):
            score += 0.35
        if doc.company_name and doc.company_name.lower() in query.lower():
            score += 0.35
        scored.append((score, doc))
    return sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]


def _decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def extract_investment_amount(query):
    """Extract actual money amounts without mistaking strike prices or horizons for stakes."""
    match = MONEY_RE.search(query) or ACTION_AMOUNT_RE.search(query)
    return _decimal(match.group(1).replace(",", "")) if match else None


def build_context(query, matches):
    amount = extract_investment_amount(query)
    month_match = MONTH_RE.search(query)
    desired_date = None
    if month_match:
        desired_date = date.today() + timedelta(days=int(month_match.group(1)) * 30)

    ranked = matches
    if desired_date:
        ranked = sorted(matches, key=lambda item: abs(((item[1].expiry_date or date.max) - desired_date).days))

    blocks = []
    citations = []
    for score, doc in ranked:
        payload = doc.payload
        stock = payload.get("stock") or {}
        target = _decimal(payload.get("target_price"))
        current = _decimal(stock.get("last_price"))
        extra = []
        if amount and amount > 0 and current and current > 0 and target is not None:
            shares = amount / current
            target_value = shares * target
            extra.append(
                f"Share scenario math: ${amount:.2f} / ${current:.2f} = {shares:.4f} shares; "
                f"at target ${target:.2f}, value = ${target_value:.2f}, change = ${target_value - amount:.2f}."
            )
        for side in ("over", "under"):
            decimal_odds = _decimal((payload.get(f"odds_{side}") or {}).get("decimal"))
            if amount and decimal_odds and decimal_odds > 0:
                extra.append(
                    f"If ${amount:.2f} were a prediction-market stake on {side} at decimal odds "
                    f"{decimal_odds}, gross payout would be ${amount * decimal_odds:.2f} "
                    f"(profit ${amount * (decimal_odds - 1):.2f}) if correct; $0 if it loses."
                )
            elif decimal_odds and decimal_odds > 0:
                example_stake = Decimal("100")
                extra.append(
                    f"Simple {side} wager example (because the user did not specify a stake): "
                    f"a $100 stake at decimal odds {decimal_odds} returns ${example_stake * decimal_odds:.2f} total "
                    f"(${example_stake * (decimal_odds - 1):.2f} profit) if correct; the full $100 stake is lost if incorrect."
                )
        blocks.append(f"[market:{doc.source_id}; relevance:{score:.3f}]\n{doc.content}\n" + " ".join(extra))
        citations.append({
            "market_id": doc.source_id,
            "symbol": doc.symbol,
            "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
            "target_price": payload.get("target_price"),
            "implied_probability_over": payload.get("implied_odds_over"),
            "implied_probability_under": payload.get("implied_odds_under"),
            "relevance": round(score, 4),
        })
    return "\n\n".join(blocks), citations
