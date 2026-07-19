from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase

from chatbot.models import MarketDocument
from chatbot.services.retrieval import retrieve_markets


class RetrievalDateTests(TestCase):
    def create_document(self, source_id, expiry, symbol="AAPL", company="Apple Inc."):
        return MarketDocument.objects.create(
            source_id=str(source_id),
            symbol=symbol,
            company_name=company,
            expiry_date=expiry,
            content=f"{symbol} market expiring {expiry}",
            content_hash=str(source_id),
            payload={"id": source_id, "stock": {"symbol": symbol, "company_name": company}},
            embedding=[1.0, 0.0],
        )

    @patch("chatbot.services.retrieval.embed_texts", return_value=[[1.0, 0.0]])
    def test_nearest_expiry_prioritizes_earliest_date_before_similarity(self, _embed):
        self.create_document(1, date(2027, 1, 15))
        self.create_document(2, date(2026, 8, 21))
        self.create_document(3, date(2026, 9, 18), symbol="META", company="Meta Platforms Inc.")

        matches = retrieve_markets("What is Apple's nearest expiry?", top_k=10)

        self.assertEqual([item[1].source_id for item in matches], ["2", "1"])

    @patch("chatbot.services.retrieval.embed_texts", return_value=[[1.0, 0.0]])
    def test_month_horizon_prioritizes_closest_expiry(self, _embed):
        near_six_months = date.today() + timedelta(days=181)
        near_two_months = date.today() + timedelta(days=60)
        self.create_document(1, near_two_months)
        self.create_document(2, near_six_months)

        matches = retrieve_markets("If I invest $300 in AAPL for 6 months", top_k=2)

        self.assertEqual(matches[0][1].source_id, "2")
