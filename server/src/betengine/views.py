import logging
from decimal import Decimal, ROUND_DOWN
import re  # For financial calculations
import uuid
import pytz
from datetime import datetime, time
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from user.models import CompetitionMember, PlatformSettings, Wallet, Transaction
from django.db.models import Sum, OuterRef, Subquery, IntegerField, Q, F, Value, Count
from django.db.models.functions import Coalesce, Abs
from django.db.models import ProtectedError
from rest_framework import generics, pagination, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.cache import cache

from betengine.utils import (  # If you need to convert back/forth
    american_to_decimal_odds,
    convert_decimal_to_american_odds,
    populate_market_from_option_data,
    decimal_to_american_odds
)
from mkt.utils import fetch_alpha_vantage_options
from taggit.models import Tag

from datetime import datetime, timedelta
from user.models import KYCProfile
from user.wallet_coins import cash_to_coins
from user.wallet_utils import get_or_create_wallet_with_starting_coins
from .models import Bet, Competition, CompetitionStatus, Market, ParlayBet, Stock
from .serializers import (  # Import Polygon's Ticker model for type hinting
    BetResolutionSerializer,
    BetSerializer,
    CompetitionLeaderboardEntrySerializer,
    CompetitionMemberSerializer,
    CompetitionSerializer,
    MarketOddsSerializer,
    ParlayBetResolutionSerializer,
    ParlayBetSerializer,
)

logger = logging.getLogger(__name__)


def _credit_winnings(user, amount: Decimal, reference: str, description: str, competition=None):
    """
    Credits winnings to the appropriate wallet bucket.
    - Competition-context bets/parlays are credited to CompetitionMember.competition_coin_balance.
    - Non-competition bets/parlays are credited to Wallet.coin_balance.
    """
    wallet, _ = get_or_create_wallet_with_starting_coins(user=user)
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

    credited_to = "coin_balance"

    if competition is not None:
        competition_member = CompetitionMember.objects.select_for_update().filter(
            competition=competition,
            user=user,
        ).first()

        if competition_member is not None:
            competition_member.competition_coin_balance += amount
            competition_member.save(update_fields=["competition_coin_balance"])
            credited_to = "competition_coin_balance"
        else:
            logger.warning(
                "Competition member not found for payout credit. Falling back to main wallet. "
                "user_id=%s competition_id=%s amount=%s",
                user.id,
                getattr(competition, "id", None),
                amount,
            )
            wallet.coin_balance += amount
            wallet.save(update_fields=["coin_balance"])
    else:
        wallet.coin_balance += amount
        wallet.save(update_fields=["coin_balance"])

    Transaction.objects.create(
        wallet=wallet,
        amount=amount,
        transaction_type=Transaction.CREDIT,
        reference=reference,
        description=description,
    )

    return credited_to


def _get_market_risk_limits(market, settings_obj=None):
    if settings_obj is None:
        settings_obj = PlatformSettings.get_instance()

    default_per_market_limit = Decimal(str(settings_obj.max_risk_tolerance or 0))
    global_limit = Decimal(
        str(getattr(settings_obj, "global_max_risk_tolerance", settings_obj.max_risk_tolerance) or 0)
    )
    configured_per_market_limit = Decimal(
        str(market.max_risk_tolerance if market.max_risk_tolerance is not None else default_per_market_limit)
    )

    effective_per_market_limit = min(configured_per_market_limit, global_limit)
    return {
        "effective_per_market_limit": effective_per_market_limit,
        "configured_per_market_limit": configured_per_market_limit,
        "global_limit": global_limit,
    }


def _max_wager_allowed_by_risk_limit(market, chosen_outcome: str, odds_decimal: Decimal, risk_limit) -> Decimal:
    """
    Returns the maximum wager allowed for a side so resulting net exposure remains within risk limit.
    net_exposure = abs(exposure_over - exposure_under)
    liability added by wager = wager * (decimal_odds - 1)
    """
    try:
        limit = Decimal(str(risk_limit or 0))
        if limit <= 0:
            return Decimal("0.00")

        per_unit_liability = Decimal(str(odds_decimal)) - Decimal("1")
        if per_unit_liability <= 0:
            return Decimal("0.00")

        current_diff = Decimal(str(market.exposure_over)) - Decimal(str(market.exposure_under))

        if chosen_outcome == "over":
            lower_liability = -limit - current_diff
            upper_liability = limit - current_diff
        else:
            lower_liability = current_diff - limit
            upper_liability = current_diff + limit

        feasible_lower = max(Decimal("0"), lower_liability)
        feasible_upper = upper_liability

        if feasible_upper < feasible_lower:
            return Decimal("0.00")

        max_wager = feasible_upper / per_unit_liability
        if max_wager <= 0:
            return Decimal("0.00")

        return max_wager.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    except Exception:
        return Decimal("0.00")


def _get_exposure_snapshot(market):
    over = Decimal(str(market.exposure_over or 0))
    under = Decimal(str(market.exposure_under or 0))
    diff = over - under
    net = abs(diff)
    dominant_side = "over" if diff > 0 else "under" if diff < 0 else None
    return over, under, diff, net, dominant_side


def _sync_market_side_locks(market, risk_limit):
    """
    Side-specific lock behavior:
    - Trigger lock when net_exposure reaches max risk tolerance.
    - Lock only the dominant side; keep opposite side open for hedging.
    - Auto-unlock when opposite-side activity brings net_exposure below max risk tolerance.
    """
    try:
        limit = Decimal(str(risk_limit or 0))
    except Exception:
        limit = Decimal("0")

    _, _, _, net, dominant_side = _get_exposure_snapshot(market)

    desired_over = False
    desired_under = False
    desired_override = False

    lock_threshold = limit if limit > 0 else Decimal("0")

    if limit > 0 and net >= lock_threshold:
        desired_override = True
        if dominant_side == "over":
            desired_over = True
        elif dominant_side == "under":
            desired_under = True

    update_fields = []
    if market.is_suspended_over != desired_over:
        market.is_suspended_over = desired_over
        update_fields.append("is_suspended_over")
    if market.is_suspended_under != desired_under:
        market.is_suspended_under = desired_under
        update_fields.append("is_suspended_under")
    if market.requires_admin_override != desired_override:
        market.requires_admin_override = desired_override
        update_fields.append("requires_admin_override")

    if update_fields:
        market.save(update_fields=update_fields)
        try:
            cache.delete(f"market_grouped_{market.stock.symbol}")
        except Exception:
            pass


def _max_wager_allowed_for_current_exposure(market, chosen_outcome: str, odds_decimal: Decimal, risk_limit) -> Decimal:
    """
    When net is already over limit, only opposite-side bets that reduce net exposure are allowed.
    Otherwise, use normal limit-preserving cap.
    """
    per_unit_liability = Decimal(str(odds_decimal)) - Decimal("1")
    if per_unit_liability <= 0:
        return Decimal("0.00")

    try:
        limit = Decimal(str(risk_limit or 0))
    except Exception:
        limit = Decimal("0")

    _, _, _, current_net, dominant_side = _get_exposure_snapshot(market)

    if limit > 0 and current_net > limit:
        if dominant_side == chosen_outcome:
            return Decimal("0.00")

        # For opposite-side hedging, require liability to stay below 2*current_net
        # so net exposure strictly decreases (prevents over-hedging to the other extreme).
        max_liability_for_reduction = (current_net * Decimal("2")) - Decimal("0.00000001")
        max_wager = max_liability_for_reduction / per_unit_liability
        if max_wager <= 0:
            return Decimal("0.00")
        return max_wager.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    return _max_wager_allowed_by_risk_limit(
        market=market,
        chosen_outcome=chosen_outcome,
        odds_decimal=odds_decimal,
        risk_limit=risk_limit,
    )

class PopulateMarketsView(APIView):
    def post(self, request):
        symbol = request.data.get("symbol", "AAPL")
        expiration = request.data.get("expiration", "2025-07-03")
        try:
            stock = Stock.objects.get(symbol=symbol.upper())
        except Stock.DoesNotExist:
            return Response({"error": "Stock not found"}, status=404)

        contracts = fetch_alpha_vantage_options(symbol, api_key=settings.ALPHA_VANTAGE_API_KEY, expiration_date=expiration)
        created = 0

        for contract_data in contracts:
            market = populate_market_from_option_data(
                stock=stock,
                target_price=contract_data["strike_price"],
                expiry_date=contract_data["expiration"],
                option_data=contract_data,
                market_model=Market,
            )
            if market:
                created += 1

        return Response({"message": f"{created} market(s) created or updated."}, status=status.HTTP_200_OK)


# class MarketDetailView(generics.RetrieveAPIView):
#     """
#     API View to retrieve comprehensive details of a single betting market by ID.
#     This allows users to view all available information for a specific market.
#     """

#     queryset = Market.objects.all().select_related("stock")

#     # The serializer_class tells DRF which serializer to use for converting the
#     # retrieved Market object into a JSON response.
#     serializer_class = MarketSerializer
#     lookup_field = "pk"
#     permission_classes = [AllowAny]

# class MarketListView(generics.ListAPIView):
#     queryset = Market.objects.filter(is_active=True)
#     serializer_class = MarketOddsSerializer


# class MarketListAPIView(generics.ListAPIView):
#     """
#     GET /markets/
#     Returns a list of all markets, each with American, decimal, and fractional odds.
#     """
#     queryset = Market.objects.all()
#     serializer_class = MarketOddsSerializer

class LoadStockTagsView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        stock_tags = request.data.get("stocks")
        if not isinstance(stock_tags, dict):
            return Response(
                {"error": "'stocks' must be a dictionary of symbol: [tags]"},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated = []
        not_found = []

        for symbol, tags in stock_tags.items():
            if not isinstance(tags, list):
                continue

            try:
                stock = Stock.objects.get(symbol=symbol.upper())
                stock.tags.set(tags)  # Replace existing tags
                stock.save()
                updated.append({symbol: tags})
            except Stock.DoesNotExist:
                not_found.append(symbol)

        return Response({
            "updated": updated,
            "not_found": not_found,
            "message": f"{len(updated)} stocks tagged. {len(not_found)} not found."
        }, status=status.HTTP_200_OK)

class StockSearchWithTagsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        tag_filter = request.query_params.get("tag", "").strip()

        stocks = Stock.objects.all()

        if query:
            stocks = stocks.filter(
                Q(symbol__icontains=query) |
                Q(company_name__icontains=query)
            )

        if tag_filter:
            stocks = stocks.filter(tags__name__iexact=tag_filter)

        # Optimize tag fetching
        stocks = stocks.prefetch_related("tags")

        results = []
        for stock in stocks:
            latest_market = Market.objects.filter(stock=stock, is_active=True).order_by('-expiry_date').first()

            results.append({
                "symbol": stock.symbol,
                "id": latest_market.id if latest_market else None,  
                "expiry_date": latest_market.expiry_date if latest_market else None,
                "company_name": stock.company_name,
                "url": stock.url,
                "tags": list(stock.tags.names())
            })

        # Fetch all unique tag names
        all_tags = list(Tag.objects.values_list("name", flat=True).distinct())

        return Response({
            "tags": all_tags,
            "results": results
        })


class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 10  # default page size
    page_size_query_param = 'page_size'
    max_page_size = 100

class MarketListAPIView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = MarketOddsSerializer
    pagination_class = StandardResultsSetPagination

    # --- Helper methods ---
    def _clean_text(self, name: str) -> str:
        raw = self.request.query_params.get(name, "")
        return str(raw).strip().rstrip("/") if raw else ""

    def _clean_bool(self, name: str) -> bool:
        return self._clean_text(name).lower() in {"true", "1", "yes", "y", "on"}

    def _clean_decimal(self, name: str):
        raw = self._clean_text(name)
        if not raw:
            return None
        safe = re.sub(r"[^\d\.\-]", "", raw)
        try:
            return Decimal(safe)
        except Exception:
            return None

    def _clean_date(self, name: str):
        raw = self._clean_text(name)
        if not raw:
            return None
        m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
        if not m:
            return None
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            return None

    # --- Main queryset ---
    def get_queryset(self):
        today = timezone.now().date()
        min_expiry = today + timedelta(days=7)    # >= 7 days
        soon_max = today + timedelta(days=14)     # <= 14 days

        # --- Cleanup expired ---
        # Market.objects.filter(expiry_date__lt=min_expiry).delete()
        expired_markets = Market.objects.filter(expiry_date__lt=min_expiry, is_active=True)

        for market in expired_markets:
            try:
                market.is_active = False
                market.save(update_fields=["is_active"])
            except ProtectedError:
                # Market has associated Bets (PROTECT is triggered)
                # → Keep it but mark inactive
                market.is_active = False
                market.save(update_fields=["is_active"])

        # --- Base queryset ---
        queryset = Market.objects.filter(
            is_active=True,
            outcome_type="over",
            expiry_date__gte=min_expiry,
        )

        # --- Query params ---
        trending = self._clean_bool("trending")
        most_viewed = self._clean_bool("most_viewed")
        recently_viewed = self._clean_bool("recently_viewed")
        expiring_soon = self._clean_bool("expiring_soon")
        search = self._clean_text("search")
        strike = self._clean_decimal("strike")
        expiry = self._clean_date("expiry")

        # --- Filters ---
        if search:
            queryset = queryset.filter(
                Q(stock__symbol__icontains=search.upper()) |
                Q(stock__company_name__icontains=search.lower())
            )

        if strike is not None:
            queryset = queryset.filter(target_price=strike)

        if expiry:
            queryset = queryset.filter(expiry_date=expiry, expiry_date__gte=min_expiry)
        elif expiring_soon:
            queryset = queryset.filter(
                expiry_date__gte=min_expiry,
                expiry_date__lte=soon_max,
            )

        # --- Odds filter ---
        queryset = queryset.filter(
            implied_odds_over__gte=Decimal("0.2"),
            implied_odds_over__lte=Decimal("0.8"),
        )

        # --- Annotations ---
        queryset = queryset.annotate(
            diff_from_fair=Abs(F("implied_odds_over") - Value(Decimal("0.5")))
        )

        # --- Ordering & distinct selection ---
        if trending:
            # Postgres DISTINCT ON (stock__symbol), pick by diff_from_fair, then volume
            queryset = (
                queryset
                .order_by("stock__symbol", "diff_from_fair", "-total_volume", "-created_at")
                .distinct("stock__symbol")
            )

        elif most_viewed:
            queryset = (
                queryset
                .order_by("stock_id", "-views_count")
                .distinct("stock_id")
            )

        elif recently_viewed:
            queryset = (
                queryset
                .order_by("stock_id", "-last_viewed_at")
                .distinct("stock_id")
            )

        elif expiring_soon and not expiry:
            queryset = (
                queryset
                .order_by("stock__symbol", "expiry_date", "diff_from_fair", "-total_volume")
                .distinct("stock__symbol")
            )

        elif search and expiry:
            queryset = queryset.order_by("target_price")

        elif search and not expiring_soon:
            queryset = queryset.order_by("diff_from_fair", "expiry_date")

        else:
            # Default ordering for distinct stocks
            queryset = (
                queryset
                .order_by("stock__symbol", "diff_from_fair", "-total_volume", "stock__company_name", "-created_at")
                .distinct("stock__symbol")
            )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class MarketDetailAPIView(generics.RetrieveAPIView):
    """
    GET /markets/<pk>/
    Returns details for a single market, including all odds formats.
    """
    queryset = Market.objects.all()
    serializer_class = MarketOddsSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        # 👇 Pass the request into serializer context for preference handling
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # ✅ Increment views
        instance.views_count += 1
        instance.last_viewed_at = timezone.now()
        instance.save(update_fields=["views_count", "last_viewed_at"])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class MarketByExpiryDateView(APIView):
    """
    Returns all Market entries matching a given expiry_date (?expiry=YYYY-MM-DD)
    and optionally filtered by stock symbol (?symbol=AAPL).
    """
    permission_classes = [AllowAny]
    serializer_class = MarketOddsSerializer
    pagination_class = StandardResultsSetPagination  # You can replace with a custom class

    def get(self, request, *args, **kwargs):
        expiry_date = request.query_params.get("expiry")
        symbol = request.query_params.get("symbol")

        if not expiry_date:
            return Response(
                {"error": "Please provide an 'expiry' query parameter in YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = Market.objects.filter(expiry_date=expiry_date, is_active=True)

        if symbol:
            queryset = queryset.filter(stock__symbol__iexact=symbol)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = MarketOddsSerializer(page, many=True, context=self.get_serializer_context())
        return paginator.get_paginated_response(serializer.data)

    def get_serializer_context(self):
        return {"request": self.request}

# class ExpiryDatesByStockSymbolView(APIView):
#     """
#     GET /markets/expiries/?symbol=AAPL
#     Returns a list of expiry dates and corresponding strikes for a given stock symbol.
#     """
#     permission_classes = [AllowAny]

#     def get(self, request, *args, **kwargs):
#         symbol = request.query_params.get("symbol")
#         if not symbol:
#             return Response(
#                 {"error": "Please provide a 'symbol' query parameter (e.g., ?symbol=AAPL)."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Get unique expiries
#         expiries = (
#             Market.objects.filter(
#                 stock__symbol__iexact=symbol,
#                 is_active=True,
#                 outcome_type="over"  # ✅ Only use 'over' rows
#             )
#             .values_list("expiry_date", flat=True)
#             .distinct()
#             .order_by("expiry_date")
#         )

#         # For each expiry, gather strikes
#         expiry_data = []
#         for expiry in expiries:
#             strikes = (
#                 Market.objects.filter(
#                     stock__symbol__iexact=symbol,
#                     expiry_date=expiry,
#                     is_active=True,
#                     outcome_type="over"
#                 )
#                 .values_list("target_price", flat=True)
#                 .distinct()
#                 .order_by("target_price")
#             )
#             expiry_data.append({
#                 "expiry_date": expiry,
#                 "strikes": list(strikes)
#             })

#         return Response({"symbol": symbol.upper(), "expiries": expiry_data}, status=status.HTTP_200_OK)

class ExpiryDatesByStockSymbolView(APIView):
    """
    GET /markets/expiries/?symbol=AAPL
    Returns a list of unique expiry dates for a given stock symbol.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        symbol = request.query_params.get("symbol")
        if not symbol:
            return Response(
                {"error": "Please provide a 'symbol' query parameter (e.g., ?symbol=AAPL)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        expiries = (
            Market.objects.filter(
                stock__symbol__iexact=symbol,
                is_active=True,
                outcome_type="over"  # ✅ Only use 'over' rows
            )
            .values_list("expiry_date", flat=True)
            .distinct()
            .order_by("expiry_date")
        )

        return Response({"symbol": symbol.upper(), "expiries": expiries}, status=status.HTTP_200_OK)
class StrikePricesByStockSymbolView(APIView):
    """
    GET /markets/strikes/?symbol=AAPL&expiry=2025-08-08
    Returns a list of unique strike prices for a given stock symbol and (optional) expiry.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        symbol = request.query_params.get("symbol")
        expiry = request.query_params.get("expiry")

        if not symbol:
            return Response(
                {"error": "Please provide a 'symbol' query parameter (e.g., ?symbol=AAPL)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Base queryset
        queryset = Market.objects.filter(
            stock__symbol__iexact=symbol,
            is_active=True,
            outcome_type="over"  # Only use 'over' rows
        )

        if expiry:
            queryset = queryset.filter(expiry_date=expiry)

        strike_prices = (
            queryset
            .values_list("target_price", flat=True)
            .distinct()
            .order_by("target_price")
        )

        return Response(
            {
                "symbol": symbol.upper(),
                "expiry": expiry,
                "strikes": strike_prices
            },
            status=status.HTTP_200_OK
        )


# class MarketByExpiryDateView(APIView):
#     """
#     Returns all Market entries matching a given expiry_date (?expiry=YYYY-MM-DD).
#     """

#     def get(self, request, *args, **kwargs):
#         expiry_date = request.query_params.get("expiry")
#         if not expiry_date:
#             return Response(
#                 {"error": "Please provide an 'expiry' query parameter in YYYY-MM-DD format."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         markets = Market.objects.filter(expiry_date=expiry_date, is_active=True)
#         serializer = MarketOddsSerializer(markets, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

class BetListAPIView(generics.ListAPIView):
    serializer_class = BetSerializer  # Use your existing BetSerializer for output
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]  # Only authenticated users can see bets

    def get_queryset(self):
        """
        Option 1: Fetch ALL bets (if appropriate for your application, e.g., for an admin)
        return Bet.objects.all().order_by('-created_at')

        Option 2: Fetch only the bets placed by the requesting user (most common scenario)
        """
        user = self.request.user
        if user.is_authenticated:
            # Filter bets by the current authenticated user
            return Bet.objects.filter(user=user).order_by("-created_at")
        return (
            Bet.objects.none()
        )  # Return an empty queryset if user is not authenticated or a public list isn't desired


class ParlayBetListAPIView(generics.ListAPIView):
    """
    API View for users to fetch their placed parlay bets.
    """

    serializer_class = (
        ParlayBetSerializer  # Use your existing ParlayBetSerializer for output
    )
    authentication_classes = [JWTAuthentication]  # If you're using JWT
    permission_classes = [
        IsAuthenticated
    ]  # Only authenticated users can see their parlays

    def get_queryset(self):
        """
        Fetches only the parlay bets placed by the requesting user.
        Prefetches related legs, markets, and stocks for efficient serialization.
        """
        user = self.request.user
        if user.is_authenticated:
            # Prefetch related data to avoid N+1 queries
            return (
                ParlayBet.objects.filter(user=user)
                .prefetch_related(
                    "legs__market__stock"  # This fetches Bet -> Market -> Stock
                )
                .order_by("-created_at")
            )
        return (
            ParlayBet.objects.none()
        )  # Return an empty queryset if user is not authenticated


# --- API View to Place a Single Bet ---

US_EASTERN = pytz.timezone("US/Eastern")

def is_market_open(now=None):
    """
    Returns True if US markets are open (Mon–Fri, 9:30am–4:00pm ET).
    """
    now = now or datetime.now(US_EASTERN)

    # Weekend check
    if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False

    # Market hours check
    market_open = time(9, 30)
    market_close = time(16, 0)
    return market_open <= now.time() <= market_close

class PlaceSingleBetAPIView(APIView):
    """
    API View for users to place a single bet on a specific market.
    Debits wallet immediately, applies exposure guardrail, and logs transaction.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        # --- KYC Rejection Check ---
        try:
            kyc_profile = user.kyc_profile
            if kyc_profile.kyc_status == "rejected":
                return Response(
                    {
                        "status": "error",
                        "message": "Your KYC has been rejected. You are not allowed to place bets.",
                        "kyc_status": kyc_profile.kyc_status,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        except KYCProfile.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": "KYC record not found. Please complete KYC verification before placing bets.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        market_id = request.data.get("market_id")
        amount_wagered = request.data.get("amount_wagered")
        chosen_outcome = request.data.get("chosen_outcome")
        competition_id = request.data.get("competition_id")

        if not all([market_id, amount_wagered, chosen_outcome]):
            return Response(
                {"status": "error", "message": "Missing market_id, amount_wagered, or chosen_outcome."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount_wagered = Decimal(str(amount_wagered))
            if amount_wagered <= 0:
                return Response(
                    {"status": "error", "message": "Wager amount must be positive."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --- Atomic section ---
            with transaction.atomic():

                # Lock market row (fetch then validate flags explicitly)
                market = Market.objects.select_for_update().get(id=market_id)

                if not market.is_active:
                    return Response(
                        {"status": "error", "message": "Betting market not active."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                settings_obj = PlatformSettings.get_instance()
                risk_limit = _get_market_risk_limits(market, settings_obj)["effective_per_market_limit"]

                _sync_market_side_locks(market, risk_limit)

                # Disallow bets on a suspended side
                if chosen_outcome == "over" and market.is_suspended_over:
                    return Response(
                        {
                            "status": "error",
                            "message": "This side is temporarily unavailable.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if chosen_outcome == "under" and market.is_suspended_under:
                    return Response(
                        {
                            "status": "error",
                            "message": "This side is temporarily unavailable.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Determine odds
                if chosen_outcome == "over":
                    odds_at_placement = market.display_odds_over
                elif chosen_outcome == "under":
                    odds_at_placement = market.display_odds_under
                else:
                    return Response(
                        {"status": "error", "message": "Invalid chosen_outcome. Must be 'over' or 'under'."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if not odds_at_placement:
                    return Response(
                        {"status": "error", "message": "Odds not available for the chosen outcome."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                odds_decimal = american_to_decimal_odds(odds_at_placement)

                # --- User max stake check ---
                profile = user.profile
                max_stake_allowed = profile.calculate_max_stake(odds_decimal)
                if amount_wagered > max_stake_allowed:
                    return Response(
                        {
                            "status": "error",
                            "message": f"Maximum allowed stake for this bet is {max_stake_allowed}. You attempted {amount_wagered}.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # --- Guardrail calculation ---
                # net_exposure = abs(exposure_over - exposure_under) represents unmatched (unhedged) positions.
                # Side lock/unlock behavior is handled by _sync_market_side_locks after exposure update.
                potential_payout = amount_wagered * odds_decimal
                liability = potential_payout - amount_wagered

                # --- Lock wallet ---
                wallet = Wallet.objects.select_for_update().get(user=user)

                competition_member = None
                debited_from = "coin_balance"

                if competition_id is not None:
                    try:
                        competition_id = int(competition_id)
                    except (TypeError, ValueError):
                        return Response(
                            {
                                "status": "error",
                                "message": "Invalid competition_id.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    competition_member = CompetitionMember.objects.select_for_update().filter(
                        competition_id=competition_id,
                        user=user,
                    ).first()

                    if not competition_member:
                        return Response(
                            {
                                "status": "error",
                                "message": "You are not a member of this competition.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if competition_member.competition_coin_balance < amount_wagered:
                        return Response(
                            {
                                "status": "error",
                                "message": "Insufficient competition wallet balance.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    competition_member.competition_coin_balance -= amount_wagered
                    competition_member.save(update_fields=["competition_coin_balance"])
                    debited_from = "competition_coin_balance"
                else:
                    if wallet.coin_balance < amount_wagered:
                        return Response(
                            {
                                "status": "error",
                                "message": "Insufficient BB coin balance.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    wallet.coin_balance -= amount_wagered
                    wallet.save(update_fields=["coin_balance", "updated_at"])

                reference = f"TRX-BET-DR-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

                bet = Bet.objects.create(
                    user=user,
                    market=market,
                    amount_wagered=amount_wagered,
                    odds_at_placement=odds_at_placement,
                    chosen_outcome=chosen_outcome,
                    status="pending",
                    is_parlay_leg=False,
                    competition=competition_member.competition if competition_member is not None else None,
                )

                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount_wagered,
                    transaction_type=Transaction.DEBIT,
                    description=f"placed bet @ id: #{bet.id} | {market.expiry_date} | {chosen_outcome.capitalize()} ${market.target_price} (-{amount_wagered} BBC)",
                    reference=reference,
                )

                # --- Update exposure ---
                if chosen_outcome == "over":
                    market.exposure_over += liability
                else:
                    market.exposure_under += liability

                market.save(update_fields=["exposure_over", "exposure_under"])
                _sync_market_side_locks(market, risk_limit)

            serializer = BetSerializer(bet)
            return Response(
                {
                    "status": "success",
                    "message": "Bet placed successfully!",
                    "bet": serializer.data,
                    "wallet_balance": str(wallet.balance),
                    "wallet_coin_balance": str(wallet.coin_balance),
                    "competition_coin_balance": (
                        str(competition_member.competition_coin_balance)
                        if competition_member is not None
                        else None
                    ),
                    "debited_from": debited_from,
                },
                status=status.HTTP_201_CREATED,
            )

        except Market.DoesNotExist:
            return Response(
                {"status": "error", "message": "Betting market not found or not active."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Wallet.DoesNotExist:
            return Response(
                {"status": "error", "message": "Wallet not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error placing single bet: {e}", exc_info=True)
            return Response(
                {"status": "error", "message": f"Unexpected error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PlaceParlayBetAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        # --- KYC Check ---
        try:
            kyc_profile = user.kyc_profile
            if kyc_profile.kyc_status == "rejected":
                return Response(
                    {
                        "status": "error",
                        "message": "Your KYC has been rejected. You are not allowed to place bets.",
                        "kyc_status": kyc_profile.kyc_status,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        except KYCProfile.DoesNotExist:
            return Response(
                {"status": "error", "message": "KYC record not found."},
                status=status.HTTP_403_FORBIDDEN,
            )

        amount_wagered = request.data.get("amount_wagered")
        legs_data = request.data.get("legs")
        competition_id = request.data.get("competition_id")

        if not all([amount_wagered, legs_data]) or not isinstance(legs_data, list) or len(legs_data) < 2:
            return Response(
                {"status": "error", "message": "Invalid parlay data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount_wagered = Decimal(str(amount_wagered))
            if amount_wagered <= 0:
                return Response(
                    {"status": "error", "message": "Wager amount must be positive."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            settings_obj = PlatformSettings.get_instance()

            combined_decimal_odds = Decimal("1")

            with transaction.atomic():

                wallet = Wallet.objects.select_for_update().get(user=user)
                competition_member = None
                debited_from = "coin_balance"

                if competition_id is not None:
                    try:
                        competition_id = int(competition_id)
                    except (TypeError, ValueError):
                        return Response(
                            {
                                "status": "error",
                                "message": "Invalid competition_id.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    competition_member = CompetitionMember.objects.select_for_update().filter(
                        competition_id=competition_id,
                        user=user,
                    ).first()

                    if not competition_member:
                        return Response(
                            {
                                "status": "error",
                                "message": "You are not a member of this competition.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if competition_member.competition_coin_balance < amount_wagered:
                        return Response(
                            {
                                "status": "error",
                                "message": "Insufficient competition wallet balance.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    if wallet.coin_balance < amount_wagered:
                        return Response(
                            {
                                "status": "error",
                                "message": "Insufficient BB coin balance.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                markets_locked = []

                # --- Lock and validate each leg ---
                for leg in legs_data:
                    market_id = leg.get("market_id")
                    chosen_outcome = leg.get("chosen_outcome")

                    market = Market.objects.select_for_update().get(id=market_id)

                    if not market.is_active:
                        return Response(
                            {"status": "error", "message": f"Market {market_id} not active."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    risk_limit = _get_market_risk_limits(market, settings_obj)["effective_per_market_limit"]
                    _sync_market_side_locks(market, risk_limit)

                    # Disallow bets on suspended sides
                    if chosen_outcome == "over" and market.is_suspended_over:
                        return Response(
                            {
                                "status": "error",
                                "message": "This side is temporarily unavailable.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if chosen_outcome == "under" and market.is_suspended_under:
                        return Response(
                            {
                                "status": "error",
                                "message": "This side is temporarily unavailable.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    odds_str = (
                        market.display_odds_over if chosen_outcome == "over"
                        else market.display_odds_under if chosen_outcome == "under"
                        else None
                    )

                    if not odds_str:
                        return Response(
                            {"status": "error", "message": f"No odds available for market {market_id}."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    odds_decimal = american_to_decimal_odds(odds_str)
                    combined_decimal_odds *= odds_decimal

                    potential_payout = amount_wagered * odds_decimal
                    liability = potential_payout - amount_wagered

                    # Guardrail check - use net exposure (abs difference) against platform risk tolerance.
                    # Hedging positions (betting opposite side) reduces net_exposure by offsetting exposures.
                    if chosen_outcome == "over":
                        new_exposure_over = market.exposure_over + liability
                        new_net_exposure = abs(new_exposure_over - market.exposure_under)
                    else:
                        new_exposure_under = market.exposure_under + liability
                        new_net_exposure = abs(market.exposure_over - new_exposure_under)

                    markets_locked.append((market, chosen_outcome, odds_str, liability))

                # --- Deduct wallet ---
                if competition_member is not None:
                    competition_member.competition_coin_balance -= amount_wagered
                    competition_member.save(update_fields=["competition_coin_balance"])
                    debited_from = "competition_coin_balance"
                else:
                    wallet.coin_balance -= amount_wagered
                    wallet.save(update_fields=["coin_balance", "updated_at"])

                reference = f"TRX-PBET-DR-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

                parlay_bet = ParlayBet.objects.create(
                    user=user,
                    competition=competition_member.competition if competition_member is not None else None,
                    amount_wagered=amount_wagered,
                    status="pending",
                    combined_odds="Calculating...",
                )

                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount_wagered,
                    transaction_type=Transaction.DEBIT,
                    description=f"placed bet(parlay) @ id: #{parlay_bet.id} with {len(legs_data)} leg(s) (-{amount_wagered} BBC)",
                    reference=reference,
                )

                # --- Create legs + update exposures ---
                for market, chosen_outcome, odds_str, liability in markets_locked:

                    Bet.objects.create(
                        user=user,
                        market=market,
                        amount_wagered=amount_wagered,
                        odds_at_placement=odds_str,
                        chosen_outcome=chosen_outcome,
                        status="pending",
                        is_parlay_leg=True,
                        parlay_bet=parlay_bet,
                        competition=competition_member.competition if competition_member is not None else None,
                    )

                    if chosen_outcome == "over":
                        market.exposure_over += liability
                    else:
                        market.exposure_under += liability

                    market.save(update_fields=["exposure_over", "exposure_under"])
                    risk_limit = _get_market_risk_limits(market, settings_obj)["effective_per_market_limit"]
                    _sync_market_side_locks(market, risk_limit)

                parlay_bet.combined_odds = decimal_to_american_odds(combined_decimal_odds)
                parlay_bet.save()

            serializer = ParlayBetSerializer(parlay_bet)
            return Response(
                {
                    "status": "success",
                    "message": "Parlay bet placed successfully!",
                    "parlay_bet": serializer.data,
                    "wallet_balance": str(wallet.balance),
                    "wallet_coin_balance": str(wallet.coin_balance),
                    "competition_coin_balance": (
                        str(competition_member.competition_coin_balance)
                        if competition_member is not None
                        else None
                    ),
                    "debited_from": debited_from,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error placing parlay bet: {e}", exc_info=True)
            return Response(
                {"status": "error", "message": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class BetResolutionAPIView(APIView):
    """
    Resolves a single bet based on the related stock's last known price (Stock.last_price).
    Once a market expires, this determines if the bet was won or lost.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]  # Can be changed to IsAdminUser later

    def post(self, request, *args, **kwargs):
        serializer = BetResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bet_id = serializer.validated_data["bet_id"]

        try:
            bet = Bet.objects.select_related("market__stock", "user").get(id=bet_id)
            market = bet.market
            stock = market.stock
            user = bet.user

            # Validate bet status
            if bet.status != "pending":
                return Response(
                    {"status": "error", "message": f"Bet {bet.id} is already {bet.status}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Ensure stock last_price is available
            if stock.last_price is None:
                return Response(
                    {"status": "error", "message": f"No available last price for {stock.symbol}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Ensure market has expired
            today = timezone.now().date()
            if market.expiry_date > today:
                return Response(
                    {"status": "error", "message": f"Market for bet {bet.id} has not expired yet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            final_price = Decimal(str(stock.last_price))
            target_price = Decimal(str(market.target_price))
            chosen_outcome = bet.chosen_outcome

            # --- Determine outcome ---
            if chosen_outcome == "over":
                bet_won = final_price >= target_price
            elif chosen_outcome == "under":
                bet_won = final_price <= target_price
            else:
                bet.status = "void"
                bet.payout_amount = Decimal("0.00")
                bet.settled_at = timezone.now()
                bet.save(update_fields=["status", "payout_amount", "settled_at"])
                return Response(
                    {"status": "void", "message": f"Invalid chosen_outcome '{chosen_outcome}' for bet {bet.id}."},
                    status=status.HTTP_200_OK,
                )

            # --- Process resolution ---
            with transaction.atomic():
                if bet_won:
                    bet.status = "won"
                    bet.payout_amount = bet.get_potential_payout()
                    payout_coins = bet.payout_amount
                    reference = f"TRX-BET-CR-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
                    credited_to = _credit_winnings(
                        user=user,
                        amount=bet.payout_amount,
                        reference=reference,
                        description=f"Payout for winning bet #{bet.id} (+{payout_coins} BBC)",
                        competition=bet.competition,
                    )
                    bet.is_paid = True

                    logger.info(
                        "✅ Bet %s WON. Credited %s BBC to %s via %s.",
                        bet.id,
                        payout_coins,
                        user.username,
                        credited_to,
                    )

                else:
                    bet.status = "lost"
                    bet.payout_amount = Decimal("0.00")
                    logger.info(f"❌ Bet {bet.id} LOST for {user.username}.")

                bet.settled_at = timezone.now()
                bet.save(update_fields=["status", "payout_amount", "settled_at", "is_paid"])

            return Response(
                {
                    "status": "success",
                    "message": f"Bet {bet.id} resolved as {bet.status}.",
                    "final_stock_price": str(final_price),
                    "payout_amount": str(bet.payout_amount),
                    "payout_coins": str(bet.payout_amount) if bet.status == "won" else "0.00",
                    "credited_to": credited_to if bet.status == "won" else None,
                    "market_target_price": str(target_price),
                    "stock_symbol": stock.symbol,
                },
                status=status.HTTP_200_OK,
            )

        except Bet.DoesNotExist:
            return Response(
                {"status": "error", "message": "Bet not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Wallet.DoesNotExist:
            return Response(
                {"status": "error", "message": "User wallet not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error resolving bet {bet_id}: {e}", exc_info=True)
            return Response(
                {"status": "error", "message": f"Unexpected error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class ResolveExpiredMarketsAPIView(APIView):
    """
    Automatically resolves all expired markets based on the stock's last_price.
    For each expired market:
      - Compares stock.last_price to market.target_price
      - Settles all pending bets in that market
      - Marks market as resolved
      - Resets exposure & suspension flags
    """

    def post(self, request, *args, **kwargs):
        today = timezone.now().date()
        expired_markets = (
            Market.objects
            .filter(expiry_date__lte=today, bets__status="pending")
            .select_related("stock")
            .distinct()
        )

        total_markets = expired_markets.count()
        resolved_bets = 0
        resolved_parlays = 0
        updated_markets = 0
        skipped_missing_price = []
        skipped_parlays_missing_price = []

        if not total_markets:
            return Response(
                {"message": "No expired markets found to resolve."},
                status=status.HTTP_200_OK
            )

        for market in expired_markets:

            stock_price = market.stock.last_price
            if stock_price is None:
                skipped_missing_price.append(
                    {
                        "market_id": market.id,
                        "symbol": market.stock.symbol,
                        "expiry_date": str(market.expiry_date),
                        "reason": "missing_stock_price",
                    }
                )
                continue  # skip if stock price unavailable

            with transaction.atomic():

                # Lock market row for safety
                market = Market.objects.select_for_update().get(id=market.id)

                pending_bets = Bet.objects.filter(market=market, status="pending", is_parlay_leg=False)

                for bet in pending_bets:
                    final_price = Decimal(str(stock_price))
                    target_price = Decimal(str(market.target_price))

                    if bet.chosen_outcome == "over":
                        bet_won = final_price >= target_price
                    elif bet.chosen_outcome == "under":
                        bet_won = final_price <= target_price
                    else:
                        bet.status = "void"
                        bet.payout_amount = Decimal("0.00")
                        bet.settled_at = timezone.now()
                        bet.save(update_fields=["status", "payout_amount", "settled_at"])
                        resolved_bets += 1
                        continue

                    bet.status = "won" if bet_won else "lost"
                    bet.payout_amount = bet.get_potential_payout() if bet_won else Decimal("0.00")
                    bet.settled_at = timezone.now()

                    bet.save(update_fields=["status", "payout_amount", "settled_at"])
                    resolved_bets += 1

                # --- Reset Guardrail Fields ---
                market.exposure_over = Decimal("0.00")
                market.exposure_under = Decimal("0.00")
                market.is_suspended_over = False
                market.is_suspended_under = False
                market.requires_admin_override = False

                # Mark market inactive
                market.is_active = False

                market.save(
                    update_fields=[
                        "exposure_over",
                        "exposure_under",
                        "is_suspended_over",
                        "is_suspended_under",
                        "requires_admin_override",
                        "is_active",
                    ]
                )

                updated_markets += 1

        # Resolve pending parlays whose legs have all expired and have price data.
        pending_parlays = ParlayBet.objects.filter(status="pending").prefetch_related("legs__market__stock")

        for parlay in pending_parlays:
            legs = list(parlay.legs.all())

            if not legs:
                continue

            if any(leg.market.expiry_date > today for leg in legs):
                continue

            missing_price_legs = [leg for leg in legs if leg.market.stock.last_price is None]
            if missing_price_legs:
                skipped_parlays_missing_price.append(
                    {
                        "parlay_id": parlay.id,
                        "missing_symbols": list({leg.market.stock.symbol for leg in missing_price_legs}),
                        "reason": "missing_stock_price",
                    }
                )
                continue

            with transaction.atomic():
                parlay = ParlayBet.objects.select_for_update().get(id=parlay.id)
                legs_qs = parlay.legs.select_related("market__stock").all()

                for leg in legs_qs:
                    if leg.status != "pending":
                        continue

                    final_price = Decimal(str(leg.market.stock.last_price))
                    target_price = Decimal(str(leg.market.target_price))

                    if leg.chosen_outcome == "over":
                        leg_won = final_price >= target_price
                    elif leg.chosen_outcome == "under":
                        leg_won = final_price <= target_price
                    else:
                        leg.status = "void"
                        leg.payout_amount = Decimal("0.00")
                        leg.settled_at = timezone.now()
                        leg.save(update_fields=["status", "payout_amount", "settled_at"])
                        continue

                    leg.status = "won" if leg_won else "lost"
                    leg.payout_amount = Decimal("0.00")
                    leg.settled_at = timezone.now()
                    leg.save(update_fields=["status", "payout_amount", "settled_at"])

                latest_leg_statuses = list(parlay.legs.values_list("status", flat=True))
                if any(status == "pending" for status in latest_leg_statuses):
                    continue

                if any(status == "void" for status in latest_leg_statuses):
                    parlay.status = "void"
                    parlay.payout_amount = Decimal("0.00")
                elif all(status == "won" for status in latest_leg_statuses):
                    parlay.status = "won"
                    parlay.payout_amount = parlay.get_potential_payout()
                else:
                    parlay.status = "lost"
                    parlay.payout_amount = Decimal("0.00")

                parlay.settled_at = timezone.now()
                parlay.save(update_fields=["status", "payout_amount", "settled_at"])
                resolved_parlays += 1

        return Response(
            {
                "message": f"✅ Resolved {updated_markets} expired markets",
                "total_markets": total_markets,
                "resolved_bets": resolved_bets,
                "resolved_parlays": resolved_parlays,
                "skipped_markets_count": len(skipped_missing_price),
                "skipped_markets": skipped_missing_price,
                "skipped_parlays_count": len(skipped_parlays_missing_price),
                "skipped_parlays": skipped_parlays_missing_price,
            },
            status=status.HTTP_200_OK,
        )
    
class CreditWinningBetsAPIView(APIView):
    """
    Credits all users for settled winnings not yet paid.
    - Singles: credit each won non-parlay Bet.
    - Parlays: credit only once at ParlayBet level after all legs are settled and parlay status is won.
    """

    def post(self, request, *args, **kwargs):
        winning_bets = Bet.objects.filter(status="won", is_paid=False, is_parlay_leg=False)
        winning_parlays = (
            ParlayBet.objects
            .filter(status="won")
            .annotate(unpaid_legs=Count("legs", filter=Q(legs__is_paid=False)))
            .filter(unpaid_legs__gt=0)
            .select_related("user", "competition")
        )

        total_credited = 0
        singles_credited = 0
        parlays_credited = 0
        total_amount = Decimal("0.00")

        if not winning_bets.exists() and not winning_parlays.exists():
            return Response(
                {"message": "No unpaid settled winnings found."},
                status=status.HTTP_200_OK,
            )

        for bet in winning_bets.select_related("user", "competition", "market__stock"):
            with transaction.atomic():
                payout_coins = bet.payout_amount

                # Generate a unique transaction reference (UUID4)
                reference = f"TRX-BET-CR-{bet.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

                _credit_winnings(
                    user=bet.user,
                    amount=bet.payout_amount,
                    reference=reference,
                    description=f"Payout for Bet #{bet.id} ({bet.market.stock.symbol}) (+{payout_coins} BBC)",
                    competition=bet.competition,
                )

                # Mark bet as paid
                bet.is_paid = True
                bet.save(update_fields=["is_paid"])

                total_credited += 1
                singles_credited += 1
                total_amount += bet.payout_amount

        for parlay in winning_parlays:
            with transaction.atomic():
                parlay_locked = ParlayBet.objects.select_for_update().get(id=parlay.id)
                leg_statuses = list(parlay_locked.legs.values_list("status", flat=True))

                if not leg_statuses or any(leg_status == "pending" for leg_status in leg_statuses):
                    continue

                if any(leg_status != "won" for leg_status in leg_statuses):
                    continue

                unpaid_legs_qs = parlay_locked.legs.filter(is_paid=False)
                if not unpaid_legs_qs.exists():
                    continue

                payout_amount = parlay_locked.payout_amount or Decimal("0.00")
                if payout_amount <= 0:
                    unpaid_legs_qs.update(is_paid=True)
                    continue

                payout_coins = payout_amount

                reference = f"TRX-PARLAY-CR-{parlay_locked.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

                _credit_winnings(
                    user=parlay_locked.user,
                    amount=payout_amount,
                    reference=reference,
                    description=f"Payout for Parlay #{parlay_locked.id} (+{payout_coins} BBC)",
                    competition=parlay_locked.competition,
                )

                unpaid_legs_qs.update(is_paid=True)

                total_credited += 1
                parlays_credited += 1
                total_amount += payout_amount

        return Response(
            {
                "message": "success",
                "total_credited": total_credited,
                "singles_credited": singles_credited,
                "parlays_credited": parlays_credited,
                "total_amount_paid": float(total_amount),
            },
            status=status.HTTP_200_OK,
        )
class ParlayBetResolutionAPIView(APIView):
    """
    API View to resolve (settle) a specific parlay bet.
    A parlay wins only if ALL its individual legs win.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]  # Or IsAdminUser for tighter control

    def post(self, request, *args, **kwargs):
        """
        Expects a JSON body with 'parlay_bet_id' to resolve a specific parlay bet.
        Example: {"parlay_bet_id": 456}
        """
        serializer = ParlayBetResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parlay_bet_id = serializer.validated_data["parlay_bet_id"]

        if not getattr(settings, "POLYGON_ENABLED", False):
            return Response(
                {
                    "error": "Polygon integration is disabled. Set POLYGON_ENABLED=true to enable parlay resolution."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            from mkt.polygon_data_fetcher import PolygonDataFetcher
        except Exception as import_error:
            logger.warning(f"Polygon integration unavailable in ParlayBetResolutionAPIView: {import_error}")
            return Response(
                {"error": "Polygon integration is unavailable in this environment."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        run_in_mock_mode = settings.POLYGON_MOCK_MODE

        if run_in_mock_mode:
            polygon_client = MockPolygonClient()
            data_fetcher = PolygonDataFetcher(client=polygon_client)
            logger.info("Parlay Bet Resolution: Using MOCK Polygon.io client.")
        else:
            api_key = settings.POLYGON_API_KEY
            if not api_key:
                return Response(
                    {
                        "error": "POLYGON_API_KEY environment variable not set for live resolution."
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            data_fetcher = PolygonDataFetcher(api_key=api_key)
            logger.info("Parlay Bet Resolution: Using LIVE Polygon.io client.")

        try:
            parlay_bet = (
                ParlayBet.objects.select_related("user")
                .prefetch_related("legs__market__stock")
                .get(id=parlay_bet_id)
            )

            if parlay_bet.status != "pending":
                return Response(
                    {
                        "error": f"Parlay bet {parlay_bet_id} is already {parlay_bet.status}."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not parlay_bet.legs.exists():
                parlay_bet.status = "void"
                parlay_bet.payout_amount = Decimal("0.00")
                parlay_bet.settled_at = timezone.now()
                parlay_bet.save()
                logger.warning(
                    f"Parlay bet {parlay_bet_id} voided: No legs found for this parlay."
                )
                return Response(
                    {
                        "message": f"Parlay bet {parlay_bet_id} voided due to missing legs.",
                        "status": parlay_bet.status,
                    },
                    status=status.HTTP_200_OK,
                )

            with transaction.atomic():
                overall_parlay_status = (
                    "won"  # Assume won initially, set to 'lost'/'void' if any leg fails
                )
                today = timezone.now().date()
                for leg in parlay_bet.legs.all():
                    # Pre-check: Ensure market has expired
                    if leg.market.expiry_date > today:
                        # If any leg's market hasn't expired, stop and return error
                        return Response(
                            {
                                "error": f"Parlay bet {parlay_bet_id} cannot be resolved yet. Market for leg {leg.id} (stock {leg.market.stock.symbol}, expiry {leg.market.expiry_date}) has not expired. (Today: {today})."
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    # If any leg is not pending, it's an integrity issue or already processed.
                    # This parlay cannot be cleanly resolved via this API.
                    if leg.status != "pending":
                        logger.error(
                            f"Leg {leg.id} of parlay {parlay_bet_id} is not pending (status: {leg.status}). This parlay might need manual review."
                        )
                        overall_parlay_status = "void"
                        break  # Stop processing legs, parlay is void

                if (
                    overall_parlay_status == "void"
                ):  # If an integrity issue was found in pre-check
                    parlay_bet.status = overall_parlay_status
                    parlay_bet.payout_amount = Decimal("0.00")
                    parlay_bet.settled_at = timezone.now()
                    parlay_bet.save()
                    return Response(
                        {
                            "message": f"Parlay bet {parlay_bet_id} voided due to internal state inconsistency.",
                            "status": parlay_bet.status,
                        },
                        status=status.HTTP_200_OK,
                    )

                # Process each leg for its outcome
                for leg in parlay_bet.legs.all():
                    market = leg.market
                    final_stock_price = data_fetcher.get_historical_stock_close(
                        stock_symbol=market.stock.symbol, query_date=market.expiry_date
                    )

                    if final_stock_price is None:
                        # If any leg cannot get historical data, the entire parlay is voided
                        leg.status = "void"
                        leg.payout_amount = Decimal("0.00")
                        leg.settled_at = timezone.now()
                        leg.save()
                        overall_parlay_status = "void"  # Set overall to void
                        logger.warning(
                            f"Leg {leg.id} of parlay {parlay_bet_id} voided: Could not get final stock price for {market.stock.symbol} on {market.expiry_date}."
                        )
                        break  # Stop processing further legs

                    leg_won = False
                    if market.outcome_type == "over":
                        leg_won = final_stock_price >= market.target_price
                    elif market.outcome_type == "under":
                        leg_won = final_stock_price <= market.target_price
                    if leg_won:
                        leg.status = "won"
                        leg.payout_amount = Decimal(
                            "0.00"
                        )  # Payout is only for the overall parlay
                    else:
                        leg.status = "lost"
                        leg.payout_amount = Decimal("0.00")
                        overall_parlay_status = (
                            "lost"  # If any leg loses, the entire parlay loses
                        )
                    leg.settled_at = timezone.now()
                    leg.save()
                    logger.info(
                        f"Leg {leg.id} (Market {market.id}) resolved as: {leg.status}"
                    )
                # Update the overall ParlayBet status and payout
                parlay_bet.status = overall_parlay_status
                if overall_parlay_status == "won":
                    # Payout for the parlay is calculated based on its combined odds at placement
                    # from utils.calculate_payout.
                    from market.utils import (
                        calculate_payout,
                    )  # Import here to avoid circular dependency issues

                    parlay_bet.payout_amount = calculate_payout(
                        parlay_bet.amount_wagered, parlay_bet.combined_odds
                    )
                    # TODO: Credit user's balance with parlay_bet.payout_amount
                    # Example: parlay_bet.user.userprofile.balance += parlay_bet.playout_amount
                    # parlay_bet.user.userprofile.save()
                    logger.info(
                        f"Parlay bet {parlay_bet.id} won. Crediting {parlay_bet.payout_amount} to user {parlay_bet.user.username}'s balance. (Placeholder)"
                    )
                else:
                    parlay_bet.payout_amount = Decimal("0.00")
                parlay_bet.settled_at = timezone.now()
                parlay_bet.save()

                return Response(
                    {
                        "message": f"Parlay bet {parlay_bet_id} resolved.",
                        "status": parlay_bet.status,
                        "payout_amount": str(parlay_bet.payout_amount),
                        "details": "Individual legs resolved based on market outcomes.",
                    },
                    status=status.HTTP_200_OK,
                )

        except ParlayBet.DoesNotExist:
            return Response(
                {"error": "Parlay bet not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while resolving parlay bet {parlay_bet_id}: {e}",
                exc_info=True,
            )
            return Response(
                {
                    "error": f"An unexpected error occurred during parlay bet resolution: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CompetitionListPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CompetitionListCreateAPIView(generics.ListCreateAPIView):
    """
    List competitions for discovery and allow authenticated users to create one.
    """

    serializer_class = CompetitionSerializer
    authentication_classes = [JWTAuthentication]
    pagination_class = CompetitionListPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = Competition.objects.select_related("creator").annotate(
            member_count=Count("members")
        )

        status_value = self.request.query_params.get("status")
        q_value = self.request.query_params.get("q")
        registration_open = self.request.query_params.get("registration_open")

        if status_value:
            queryset = queryset.filter(status=status_value)

        if q_value:
            queryset = queryset.filter(
                Q(name__icontains=q_value) | Q(description__icontains=q_value)
            )

        if registration_open in ["true", "1", "yes"]:
            now = timezone.now()
            queryset = queryset.filter(
                status=CompetitionStatus.REGISTRATION,
            ).filter(
                Q(registration_close_date__isnull=True, start_date__gt=now)
                | Q(registration_close_date__gt=now)
            )

        ordering = self.request.query_params.get("ordering", "-created_at")
        if ordering in ["created_at", "-created_at", "start_date", "-start_date", "end_date", "-end_date"]:
            queryset = queryset.order_by(ordering)

        return queryset

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user, status=CompetitionStatus.REGISTRATION)


class CompetitionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CompetitionSerializer
    permission_classes = [AllowAny]
    queryset = Competition.objects.select_related("creator").annotate(
        member_count=Count("members")
    )
    lookup_field = "pk"


class CompetitionJoinAPIView(APIView):
    """
    Join a competition if registration is open and capacity remains.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, competition_id):
        try:
            competition = Competition.objects.select_for_update().get(pk=competition_id)
        except Competition.DoesNotExist:
            return Response(
                {"error": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        competition.update_status()

        existing_membership = CompetitionMember.objects.filter(
            competition=competition,
            user=request.user,
        ).first()
        if existing_membership:
            wallet, _ = get_or_create_wallet_with_starting_coins(user=request.user)
            payload = {
                "competition_id": competition.id,
                "joined": True,
                "current_member_count": competition.members.count(),
                "max_members": competition.max_members,
                "remaining_bb_cash_balance": str(wallet.balance),
                "message": "You already joined this competition.",
            }
            return Response(payload, status=status.HTTP_200_OK)

        if not competition.is_registration_open:
            return Response(
                {"error": "Registration is closed for this competition."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_member_count = CompetitionMember.objects.filter(
            competition=competition
        ).count()
        if current_member_count >= competition.max_members:
            return Response(
                {"error": "Competition is full."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet, _ = get_or_create_wallet_with_starting_coins(user=request.user)
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        entry_fee = Decimal(str(competition.entry_fee or 0))
        if entry_fee > 0:
            if wallet.balance < entry_fee:
                return Response(
                    {
                        "error": (
                            "Insufficient BB cash balance for entry fee. "
                            "Please fund your BB cash wallet to join this competition."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            wallet.balance -= entry_fee
            wallet.save(update_fields=["balance"])

            reference = (
                f"TRX-COMP-ENTRY-{competition.id}-"
                f"{timezone.now().strftime('%Y%m%d%H%M%S')}-"
                f"{uuid.uuid4().hex[:6].upper()}"
            )
            Transaction.objects.create(
                wallet=wallet,
                amount=entry_fee,
                transaction_type=Transaction.DEBIT,
                reference=reference,
                description=f"Entry fee for competition #{competition.id} ({competition.name})",
                status=Transaction.SUCCESSFUL,
            )

        CompetitionMember.objects.create(
            competition=competition,
            user=request.user,
            competition_coin_balance=competition.starting_coin_balance,
        )

        payload = {
            "competition_id": competition.id,
            "joined": True,
            "current_member_count": current_member_count + 1,
            "max_members": competition.max_members,
            "remaining_bb_cash_balance": str(wallet.balance),
            "message": "Successfully joined competition.",
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class CompetitionLeaderboardAPIView(generics.ListAPIView):
    """
    Returns participants and their stats for a competition leaderboard page.
    """

    serializer_class = CompetitionLeaderboardEntrySerializer
    permission_classes = [AllowAny]
    pagination_class = CompetitionListPagination

    def get_queryset(self):
        competition_id = self.kwargs.get("competition_id")
        queryset = CompetitionMember.objects.filter(
            competition_id=competition_id,
            is_disqualified=False,
        ).select_related("user", "competition")

        # Sort by finalized rank if available; otherwise by join date.
        return queryset.order_by("final_rank", "joined_at")


class CompetitionMembershipListAPIView(generics.ListAPIView):
    """
    Returns all competitions joined by the authenticated user.
    """

    serializer_class = CompetitionMemberSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CompetitionListPagination

    def get_queryset(self):
        return CompetitionMember.objects.filter(user=self.request.user).select_related(
            "competition", "user"
        )
