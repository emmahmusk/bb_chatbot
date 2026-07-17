from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from chatbot.models import MarketDocument
from chatbot.services.indexer import sync_market_index
from chatbot.services.retrieval import extract_investment_amount
from chatbot.services.openai_client import StructuredAnswer


MARKET = {
    "id": 42,
    "stock": {
        "symbol": "AAPL",
        "company_name": "Apple Inc.",
        "last_price": "200.00",
    },
    "target_price": "220.00",
    "expiry_date": "Thu, 15 Jan 2027",
    "outcome_type": "over",
    "implied_odds_over": "0.6000",
    "implied_odds_under": "0.4000",
    "odds_over": {"american": "-150", "decimal": "1.67", "fractional": "2/3"},
    "odds_under": {"american": "+150", "decimal": "2.50", "fractional": "3/2"},
    "is_active": True,
}


class MarketIndexTests(TestCase):
    @patch("chatbot.services.indexer.embed_texts", return_value=[[1.0, 0.0]])
    @patch("chatbot.services.indexer.iter_markets", return_value=iter([MARKET]))
    def test_sync_indexes_human_readable_expiry(self, _markets, _embeddings):
        result = sync_market_index()
        document = MarketDocument.objects.get(source_id="42")
        self.assertEqual(document.expiry_date, date(2027, 1, 15))
        self.assertEqual(result["indexed"], 1)

    def test_strike_price_is_not_mistaken_for_wager_amount(self):
        query = "What's the difference between buying one share of META and wagering on META > 620?"
        self.assertIsNone(extract_investment_amount(query))

    def test_explicit_money_amount_is_extracted(self):
        self.assertEqual(extract_investment_amount("invest $300 in AAPL"), 300)

    def test_structured_answer_removes_formatting_markers(self):
        answer = StructuredAnswer(
            summary="**Direct answer**",
            sections=[{
                "heading": "### Market facts",
                "points": [{"label": "**Ticker**", "text": "- **AAPL** is Apple", "style": "standard"}],
            }],
            disclaimer="*Educational only - not financial advice.*",
        )
        self.assertEqual(answer.summary, "Direct answer")
        self.assertEqual(answer.sections[0].heading, "Market facts")
        self.assertEqual(answer.sections[0].points[0].label, "Ticker")
        self.assertEqual(answer.sections[0].points[0].text, "AAPL is Apple")


class ChatAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        MarketDocument.objects.create(
            source_id="42",
            symbol="AAPL",
            company_name="Apple Inc.",
            expiry_date=date(2027, 1, 15),
            content="Apple market context",
            content_hash="hash",
            payload=MARKET,
            embedding=[1.0, 0.0],
        )

    @patch("chatbot.views.generate_answer", return_value={
        "summary": "A careful market answer.",
        "sections": [{
            "heading": "Key difference",
            "points": [{"label": "Ownership", "text": "Shares represent ownership.", "style": "insight"}],
        }],
        "disclaimer": "Educational only - not financial advice.",
    })
    @patch("chatbot.services.retrieval.embed_texts", return_value=[[1.0, 0.0]])
    def test_chat_returns_answer_and_market_sources(self, _embed, _answer):
        response = self.client.post(
            "/api/chat/",
            {"message": "If I invest $300 in AAPL for 6 months?"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sources"][0]["market_id"], "42")
        self.assertIn("A careful market answer.", response.data["answer"])
        self.assertEqual(response.data["structured_answer"]["sections"][0]["heading"], "Key difference")

    def test_health(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["indexed_markets"], 1)

    def test_chat_page_uses_bullbear_assets(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BullBear Market Intelligence")
        self.assertContains(response, "chatbot/images/bullbear_logo.png")
