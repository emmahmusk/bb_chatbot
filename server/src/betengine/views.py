import logging
from decimal import Decimal, ROUND_DOWN
import re  # For financial calculations
import uuid
import pytz
from datetime import datetime, time
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from user.models import PlatformSettings, Wallet, Transaction
from django.db.models import Sum, OuterRef, Subquery, IntegerField, Q, F, Value
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
from .models import Bet, Market, ParlayBet, Stock
from .serializers import (  # Import Polygon's Ticker model for type hinting
    BetResolutionSerializer,
    BetSerializer,
    MarketOddsSerializer,
    ParlayBetResolutionSerializer,
    ParlayBetSerializer,
)

logger = logging.getLogger(__name__)


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

                # Disallow bets on a suspended side
                if chosen_outcome == "over" and market.is_suspended_over:
                    return Response(
                        {"status": "error", "message": "Over side for this market is suspended."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if chosen_outcome == "under" and market.is_suspended_under:
                    return Response(
                        {"status": "error", "message": "Under side for this market is suspended."},
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
                # Users can hedge by betting the opposite side, which reduces net_exposure and may unlock markets.
                # This is compared against PlatformSettings.max_risk_tolerance to ensure platform risk limits aren't exceeded.
                settings_obj = PlatformSettings.get_instance()
                risk_limit = settings_obj.max_risk_tolerance

                potential_payout = amount_wagered * odds_decimal
                liability = potential_payout - amount_wagered

                max_allowed_by_risk = _max_wager_allowed_by_risk_limit(
                    market=market,
                    chosen_outcome=chosen_outcome,
                    odds_decimal=odds_decimal,
                    risk_limit=risk_limit,
                )
                effective_max_allowed = min(max_stake_allowed, max_allowed_by_risk)

                if amount_wagered > effective_max_allowed:
                    return Response(
                        {
                            "status": "error",
                            "message": (
                                f"Bet limit reached for this side. You can wager up to {effective_max_allowed} "
                                f"on {chosen_outcome.upper()} for market {market.id} under current risk settings."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # --- Lock wallet ---
                wallet = Wallet.objects.select_for_update().get(user=user)

                if wallet.balance < amount_wagered:
                    return Response(
                        {"status": "error", "message": "Insufficient wallet balance."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Deduct wallet
                wallet.balance -= amount_wagered
                wallet.locked_balance += amount_wagered
                wallet.save(update_fields=["balance", "locked_balance", "updated_at"])

                reference = f"TRX-BET-DR-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

                bet = Bet.objects.create(
                    user=user,
                    market=market,
                    amount_wagered=amount_wagered,
                    odds_at_placement=odds_at_placement,
                    chosen_outcome=chosen_outcome,
                    status="pending",
                    is_parlay_leg=False,
                )

                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount_wagered,
                    transaction_type=Transaction.DEBIT,
                    description=f"placed bet @ id: #{bet.id} | {market.expiry_date} | {chosen_outcome.capitalize()} ${market.target_price}",
                    reference=reference,
                )

                # --- Update exposure ---
                if chosen_outcome == "over":
                    market.exposure_over += liability
                else:
                    market.exposure_under += liability

                market.save(update_fields=["exposure_over", "exposure_under"])

            serializer = BetSerializer(bet)
            return Response(
                {
                    "status": "success",
                    "message": "Bet placed successfully!",
                    "bet": serializer.data,
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
            risk_limit = settings_obj.max_risk_tolerance

            combined_decimal_odds = Decimal("1")

            with transaction.atomic():

                wallet = Wallet.objects.select_for_update().get(user=user)
                if wallet.balance < amount_wagered:
                    return Response(
                        {"status": "error", "message": "Insufficient balance."},
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

                    # Disallow bets on suspended sides
                    if chosen_outcome == "over" and market.is_suspended_over:
                        return Response(
                            {"status": "error", "message": f"Over side suspended for market {market_id}."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if chosen_outcome == "under" and market.is_suspended_under:
                        return Response(
                            {"status": "error", "message": f"Under side suspended for market {market_id}."},
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

                    # Validate net_exposure against PlatformSettings.max_risk_tolerance
                    max_allowed_by_risk = _max_wager_allowed_by_risk_limit(
                        market=market,
                        chosen_outcome=chosen_outcome,
                        odds_decimal=odds_decimal,
                        risk_limit=risk_limit,
                    )
                    if amount_wagered > max_allowed_by_risk:
                        return Response(
                            {
                                "status": "error",
                                "message": (
                                    f"Bet limit reached for market {market_id} ({chosen_outcome.upper()}). "
                                    f"You can wager up to {max_allowed_by_risk} under current risk settings."
                                ),
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    markets_locked.append((market, chosen_outcome, odds_str, liability))

                # --- Deduct wallet ---
                wallet.balance -= amount_wagered
                wallet.locked_balance += amount_wagered
                wallet.save(update_fields=["balance", "locked_balance", "updated_at"])

                reference = f"TRX-PBET-DR-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

                parlay_bet = ParlayBet.objects.create(
                    user=user,
                    amount_wagered=amount_wagered,
                    status="pending",
                    combined_odds="Calculating...",
                )

                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount_wagered,
                    transaction_type=Transaction.DEBIT,
                    description=f"placed bet(parlay) @ id: #{parlay_bet.id} with {len(legs_data)} leg(s)",
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
                    )

                    if chosen_outcome == "over":
                        market.exposure_over += liability
                    else:
                        market.exposure_under += liability

                    market.save(update_fields=["exposure_over", "exposure_under"])

                parlay_bet.combined_odds = decimal_to_american_odds(combined_decimal_odds)
                parlay_bet.save()

            serializer = ParlayBetSerializer(parlay_bet)
            return Response(
                {
                    "status": "success",
                    "message": "Parlay bet placed successfully!",
                    "parlay_bet": serializer.data,
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
                    payout_coins = cash_to_coins(bet.payout_amount)

                    # ✅ Credit wallet in BullBear Coins
                    wallet = Wallet.objects.select_for_update().get(user=user)
                    wallet.coin_balance += payout_coins
                    wallet.save(update_fields=["coin_balance"])
                    reference = f"TRX-BET-CR-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
                    # ✅ Log transaction
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=bet.payout_amount,
                        transaction_type=Transaction.CREDIT,
                        description=f"Payout for winning bet #{bet.id} (+{payout_coins} BBC)",
                        reference=reference,
                    )

                    logger.info(f"✅ Bet {bet.id} WON. Credited {payout_coins} BBC to {user.username}.")

                else:
                    bet.status = "lost"
                    bet.payout_amount = Decimal("0.00")
                    logger.info(f"❌ Bet {bet.id} LOST for {user.username}.")

                bet.settled_at = timezone.now()
                bet.save(update_fields=["status", "payout_amount", "settled_at"])

            return Response(
                {
                    "status": "success",
                    "message": f"Bet {bet.id} resolved as {bet.status}.",
                    "final_stock_price": str(final_price),
                    "payout_amount": str(bet.payout_amount),
                    "payout_coins": str(cash_to_coins(bet.payout_amount)) if bet.status == "won" else "0.00",
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
        expired_markets = Market.objects.filter(expiry_date__lte=today, is_active=True)

        total_markets = expired_markets.count()
        resolved_bets = 0
        updated_markets = 0

        if not total_markets:
            return Response(
                {"message": "No expired markets found to resolve."},
                status=status.HTTP_200_OK
            )

        for market in expired_markets.select_related("stock"):

            stock_price = market.stock.last_price
            if stock_price is None:
                continue  # skip if stock price unavailable

            winning_side = "over" if stock_price > market.target_price else "under"

            with transaction.atomic():

                # Lock market row for safety
                market = Market.objects.select_for_update().get(id=market.id)

                pending_bets = Bet.objects.filter(market=market, status="pending")

                for bet in pending_bets:
                    bet.status = "won" if bet.chosen_outcome == winning_side else "lost"
                    bet.payout_amount = (
                        bet.get_potential_payout()
                        if bet.status == "won"
                        else Decimal("0.00")
                    )
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

        return Response(
            {
                "message": f"✅ Resolved {updated_markets} expired markets",
                "total_markets": total_markets,
                "resolved_bets": resolved_bets,
            },
            status=status.HTTP_200_OK,
        )
    
class CreditWinningBetsAPIView(APIView):
    """
    Credits all users whose bets are won but not yet paid.
    Creates a Transaction record for each wallet credit using UUID reference.
    """

    def post(self, request, *args, **kwargs):
        winning_bets = Bet.objects.filter(status="won", is_paid=False)
        total_credited = 0
        total_amount = Decimal("0.00")

        if not winning_bets.exists():
            return Response(
                {"message": "No unpaid winning bets found."},
                status=status.HTTP_200_OK,
            )

        for bet in winning_bets.select_related("user"):
            with transaction.atomic():
                wallet, _ = get_or_create_wallet_with_starting_coins(user=bet.user)
                payout_coins = cash_to_coins(bet.payout_amount)

                # Generate a unique transaction reference (UUID4)
                reference = f"TRX-BET-CR-{bet.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

                # Update wallet coin balance
                wallet.coin_balance += payout_coins
                wallet.save(update_fields=["coin_balance"])

                # Create Transaction log
                Transaction.objects.create(
                    wallet=wallet,
                    amount=bet.payout_amount,
                    transaction_type=Transaction.CREDIT,
                    reference=reference,
                    description=f"Payout for Bet #{bet.id} ({bet.market.stock.symbol}) (+{payout_coins} BBC)"
                )

                # Mark bet as paid
                bet.is_paid = True
                bet.save(update_fields=["is_paid"])

                total_credited += 1
                total_amount += bet.payout_amount

        return Response(
            {
                "message": "success",
                "total_credited": total_credited,
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
