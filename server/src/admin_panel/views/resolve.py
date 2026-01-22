# betting/views/admin/resolve.py
from django.utils.timezone import now

from betting.models.bet import Bet
from betting.models.transaction import TransactionLog
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView


class AdminResolveBetView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, bet_id):
        try:
            bet = Bet.objects.get(id=bet_id)
        except Bet.DoesNotExist:
            return Response(
                {"error": "Bet not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if bet.status != "open":
            return Response(
                {"error": "Bet already resolved."}, status=status.HTTP_400_BAD_REQUEST
            )

        result_price = request.data.get("result_price")
        if result_price is None:
            return Response(
                {"error": "Result price is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bet.result_price = result_price
        bet.resolved_at = now()

        # Evaluate bet outcome
        won = False
        if bet.bet_type == "over" and float(result_price) > float(bet.target_price):
            won = True
        elif bet.bet_type == "under" and float(result_price) < float(bet.target_price):
            won = True

        if won:
            bet.status = "won"
            payout = bet.stake * bet.odds
            bet.user.balance += payout
            TransactionLog.objects.create(
                user=bet.user,
                type="payout",
                amount=payout,
                metadata={"bet_id": bet.id, "symbol": bet.symbol},
            )
            bet.user.save()
        else:
            bet.status = "lost"

        bet.save()
        return Response({"bet_id": bet.id, "status": bet.status})
