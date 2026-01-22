# src/adminpanel/views/settlements.py

from rest_framework.response import Response
from rest_framework.views import APIView


class PendingSettlementsView(APIView):
    def get(self, request):
        return Response(
            [
                {"bet_id": 1, "user": "john", "ticker": "TSLA"},
                {"bet_id": 2, "user": "emma", "ticker": "NVDA"},
            ]
        )


class ResolveSettlementView(APIView):
    def post(self, request, bet_id):
        outcome = request.data.get("outcome")
        return Response({"message": f"Bet {bet_id} marked as {outcome}"})
