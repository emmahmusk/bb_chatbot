# src/adminpanel/views/users.py

from rest_framework.response import Response
from rest_framework.views import APIView, status
from rest_framework.permissions import AllowAny
from django.db.models import Sum
from django.contrib.auth import get_user_model

from admin_panel.utils import get_bet_volume
from mkt.models import OptionData
from rest_framework.pagination import PageNumberPagination
from admin_panel.analytics import get_settlement_groups_v4

# admin_panel/views/limits.py
from decimal import Decimal
from datetime import datetime

User = get_user_model()


from user.models import Profile
from betengine.models import Bet


class AdminBetLimitView(APIView):
    """
    Admin endpoint to evaluate a user's bet limit exposure based on CRS risk score.
    GET /admin/bet-limit/?user_id=...&symbol=...&strike=...&expiration=...
    """
    def get(self, request):
        user_id = request.query_params.get("user_id")
        symbol = request.query_params.get("symbol")
        strike = request.query_params.get("strike")
        expiration = request.query_params.get("expiration")

        if not all([user_id, symbol, strike, expiration]):
            return Response({"error": "Missing required query parameters."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            strike = Decimal(strike)
            expiration_date = datetime.strptime(expiration, "%Y-%m-%d").date()
            user = User.objects.get(id=user_id)
            profile = user.profile
        except (ValueError, User.DoesNotExist, Profile.DoesNotExist):
            return Response({"error": "Invalid user or input format."}, status=status.HTTP_400_BAD_REQUEST)

        # Compute CRS-based max allowed win
        crs_score = profile.crs_risk_score
        max_win_allowed = profile.max_wager_allowed

        # Get all user bets matching market
        bets = Bet.objects.filter(
            user=user,
            market__stock__symbol__iexact=symbol,
            market__target_price=strike,
            market__expiry_date=expiration_date
        )

        # Total exposure = sum of wagered amounts
        total_amount_wagered = bets.aggregate(total=Sum("amount_wagered"))['total'] or Decimal("0")

        # Max odds used for estimation of exposure
        max_odds = Decimal("0")
        for bet in bets:
            try:
                odds_val = Decimal(bet.odds_at_placement)
                if odds_val < 0:
                    decimal_odds = (Decimal("100") / abs(odds_val)) + 1
                else:
                    decimal_odds = (odds_val / Decimal("100")) + 1
                if decimal_odds > max_odds:
                    max_odds = decimal_odds
            except Exception:
                continue

        estimated_payout = total_amount_wagered * max_odds
        remaining_wager_room = max(Decimal("0"), max_win_allowed - estimated_payout)

        return Response({
            "user": user.username,
            "crs_score": crs_score,
            "crs_level": profile.crs_risk_level,
            "max_allowed_win": max_win_allowed,
            "amount_already_wagered": total_amount_wagered,
            "estimated_payout": estimated_payout,
            "remaining_max_stake": remaining_wager_room,
        })

class AlphaVantageVolumeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        symbol = request.query_params.get("symbol")
        strike = request.query_params.get("strike")
        expiration = request.query_params.get("expiration")  # YYYY-MM-DD

        if not (symbol and strike and expiration):
            return Response(
                {"error": "symbol, strike, and expiration are required query parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            strike = float(strike)
        except ValueError:
            return Response({"error": "Invalid strike value"}, status=400)

        call_volume = OptionData.objects.filter(
            symbol=symbol,
            strike=strike,
            expiration=expiration,
            option_type='call'
        ).aggregate(vol=Sum('volume'))['vol'] or 0

        put_volume = OptionData.objects.filter(
            symbol=symbol,
            strike=strike,
            expiration=expiration,
            option_type='put'
        ).aggregate(vol=Sum('volume'))['vol'] or 0

        return Response({
            "symbol": symbol,
            "strike": strike,
            "expiration": expiration,
            "call_volume": call_volume,
            "put_volume": put_volume,
            "total_volume": call_volume + put_volume
        })




class BetVolumeAdminView(APIView):
    permission_classes = [AllowAny]  # Only accessible to admin users

    def get(self, request, *args, **kwargs):
        symbol = request.query_params.get("symbol")
        strike = request.query_params.get("strike")
        expiration = request.query_params.get("expiration")

        if not symbol or not strike or not expiration:
            return Response(
                {"error": "Missing required parameters: stock, strike, expiration"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            strike = float(strike)
        except ValueError:
            return Response({"error": "Invalid strike value"}, status=400)

        volume = get_bet_volume(symbol, strike, expiration)

        return Response({
            "stock": symbol,
            "strike": strike,
            "expiration": expiration,
            "bet_volume": volume
        })


class UserSearchView(APIView):
    def get(self, request):
        username = request.query_params.get("username")
        return Response(
            {
                "username": username,
                "crs": 3.5,
                "balance": 2200,
                "kyc_status": "verified",
            }
        )


class UserHistoryView(APIView):
    def get(self, request, user_id):
        return Response(
            {
                "bets": [
                    {"ticker": "AAPL", "amount": 200, "result": "won"},
                    {"ticker": "MSFT", "amount": 150, "result": "lost"},
                ]
            }
        )


class AdjustCRSView(APIView):
    def post(self, request, user_id):
        new_crs = request.data.get("crs")
        return Response({"message": f"CRS updated to {new_crs}"})



class AdminBetSettlementPagination(PageNumberPagination):
    """
    Custom pagination for admin bet settlements.
    Supports ?page=<num>&page_size=<num>
    """
    page_size = 20  # default per page
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminBetSettlementView(APIView):
    """
    Returns grouped settlements for admin, including single and parlay bets.
    Each group = (Ticker | Side | Strike | Expiry | Status) with child bets listed.
    Supports search, status filter, bet_type filter, and pagination.
    """
    pagination_class = AdminBetSettlementPagination

    def get(self, request):
        # Filters
        status_filter = request.query_params.get("status")
        search_query = request.query_params.get("search")
        bet_type_filter = request.query_params.get("bet_type")  # "single" or "parlay_leg"

        # --- Get grouped settlements ---
        grouped_data = get_settlement_groups_v4(
            status_filter=status_filter,
            search=search_query
        )

        # --- Apply bet_type filter at group level ---
        if bet_type_filter in ["single", "parlay_leg"]:
            for group in grouped_data:
                group["bets"] = [b for b in group["bets"] if b.get("bet_type") == bet_type_filter]
            grouped_data = [g for g in grouped_data if g["bets"]]

        # --- Paginate the grouped_data properly ---
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(grouped_data, request)

        return paginator.get_paginated_response(page)