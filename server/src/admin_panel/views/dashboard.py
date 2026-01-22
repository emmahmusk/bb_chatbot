# admin_panel/views/dashboard.py
from datetime import date

from django.db.models import Sum

from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_panel.permissions import IsAdmin
from admin_panel.serializers import BetSerializer
from betengine.models import Bet, TransactionLog
from user.models import KYCProfile, User

# views/admin_dashboard.py

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAdminUser


class OpenBetsAdminView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Filter open and confirmed bets
        queryset = Bet.objects.filter(status="open", is_confirmed=True)

        # Optional filters
        user_id = request.query_params.get("user_id")
        stock_symbol = request.query_params.get("stock_symbol")

        if user_id:
            queryset = queryset.filter(user__id=user_id)

        if stock_symbol:
            queryset = queryset.filter(stock__symbol__iexact=stock_symbol)

        serializer = BetSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# src/adminpanel/views/dashboard.py


class MockAdminSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Dummy payload - hook into analytics service/model later
        return Response(
            {
                "daily_volume": 100000,
                "active_users": 245,
                "pnl_today": 4500,
                "top_users": [
                    {"username": "protrader", "pnl": 2400},
                    {"username": "riskybiz", "pnl": 1600},
                ],
            }
        )


class KPISummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        today = date.today()
        total_volume = (
            Bet.objects.filter(date_created__date=today).aggregate(Sum("stake"))[
                "stake__sum"
            ]
            or 0
        )
        total_users = User.objects.count()
        pnl_by_day = (
            Bet.objects.filter(date_created__date=today).aggregate(Sum("payout"))[
                "payout__sum"
            ]
            or 0
        )

        top_users = User.objects.annotate(total_win=Sum("bets__payout")).order_by(
            "-total_win"
        )[:5]
        top_users_list = [
            {"username": u.username, "payout": u.total_win} for u in top_users
        ]

        return Response(
            {
                "daily_volume": total_volume,
                "active_users": total_users,
                "daily_pnl": pnl_by_day,
                "top_users": top_users_list,
            }
        )


class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_users = User.objects.count()
        verified_users = User.objects.filter(is_kyc_verified=True).count()

        open_bets = Bet.objects.filter(status="open").count()
        total_bets = Bet.objects.count()
        total_staked = Bet.objects.aggregate(total=Sum("stake"))["total"] or 0
        total_payout = (
            TransactionLog.objects.filter(type="payout").aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )

        pending_kyc = KYCProfile.objects.filter(kyc_status="pending").count()
        approved_kyc = KYCProfile.objects.filter(kyc_status="approved").count()

        return Response(
            {
                "users": {"total": total_users, "verified": verified_users},
                "bets": {
                    "open": open_bets,
                    "total": total_bets,
                    "staked_amount": total_staked,
                    "total_payouts": total_payout,
                },
                "kyc": {"pending": pending_kyc, "approved": approved_kyc},
            }
        )
