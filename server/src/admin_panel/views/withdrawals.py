# src/adminpanel/views/withdrawals.py

from rest_framework.response import Response
from rest_framework.views import APIView


class WithdrawalListView(APIView):
    def get(self, request):
        return Response(
            [
                {"user_id": 1, "amount": 5000, "status": "pending"},
                {"user_id": 2, "amount": 12000, "status": "flagged"},
            ]
        )


class ApproveWithdrawalView(APIView):
    def post(self, request, withdrawal_id):
        return Response({"message": f"Withdrawal {withdrawal_id} approved"})
