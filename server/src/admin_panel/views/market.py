import logging
from django.db import transaction
from admin_panel.utils import get_grouped_market_data
from collections import defaultdict
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.management import call_command  # To run Django management commands
from django.core.cache import cache
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny  # Or a more custom admin permission
from rest_framework.response import Response
from rest_framework.views import APIView
from betengine.models import Stock, Market
from betengine.utils import american_to_decimal_odds, american_to_fractional_odds
from betengine.serializers import StockAdminSerializer
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
# Import your serializers
from django.utils import timezone
from mkt.utils import get_side_and_american_odds
from mkt.market_chart import ODDS_LADDER_JSON
logger = logging.getLogger(__name__)
from datetime import datetime
def round_two_places(value):
    """Safely round any numeric-like value to two decimal places."""
    try:
        if value is None or value == "" or value == "-":
            return None
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError):
        return None


# def american_to_decimal_odds(american_odds):
#     """Convert American odds to decimal odds safely."""
#     try:
#         if american_odds in [None, "", "-"]:
#             return None
#         american_odds = float(american_odds)
#         if american_odds > 0:
#             return 1 + (american_odds / 100)
#         elif american_odds < 0:
#             return 1 + (100 / abs(american_odds))
#         return None
#     except (TypeError, ValueError):
#         return None


class StockListView(APIView):
    """
    Returns a list of all stocks with cached price data.
    Cache TTL: 60 seconds (configurable).
    """

    CACHE_KEY = "stock_admin_list"
    CACHE_TTL = 60  # seconds

    def get(self, request):
        # ✅ Try to serve from cache
        cached_data = cache.get(self.CACHE_KEY)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # ✅ Fetch fresh data if not cached
        stocks = Stock.objects.all().order_by("company_name")
        serializer = StockAdminSerializer(stocks, many=True)
        data = serializer.data

        # ✅ Cache serialized result for performance
        cache.set(self.CACHE_KEY, data, timeout=self.CACHE_TTL)

        return Response(data, status=status.HTTP_200_OK)
class StockToggleUpdateView(APIView):
    """
    Updates a stock's `market_status` and/or `auto_odds` fields.
    When `market_status` changes, all related markets' `is_active`
    fields are bulk updated accordingly.

    Returns the full updated stock list so frontend can refresh its display.
    """

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        stock_id = kwargs.get("pk")

        try:
            stock = Stock.objects.get(pk=stock_id)
        except Stock.DoesNotExist:
            return Response({"error": "Stock not found."}, status=status.HTTP_404_NOT_FOUND)

        prev_market_status = stock.market_status
        updated_fields = []

        # Normalize boolean values safely
        def to_bool(value):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ["true", "1", "yes", "y"]
            if isinstance(value, int):
                return value == 1
            return False

        # Apply valid updates
        for field in ["market_status", "auto_odds"]:
            if field in request.data:
                value = request.data[field]
                if field in ["market_status", "auto_odds"]:
                    value = to_bool(value)
                setattr(stock, field, value)
                updated_fields.append(field)

        # Save only if any fields were changed
        if updated_fields:
            stock.save(update_fields=updated_fields)

        # Bulk update related markets if market_status changed
        if "market_status" in updated_fields and stock.market_status != prev_market_status:
            Market.objects.filter(stock=stock).update(is_active=stock.market_status)

        # Invalidate stock cache to reflect new toggle state instantly
        cache.delete("stock_admin_list")

        # Return full updated stock list for frontend refresh
        updated_stocks = Stock.objects.all().order_by("symbol")
        serializer = StockAdminSerializer(updated_stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class GroupedMarketView(APIView):
    """
    Returns grouped markets by expiry date and target price.
    Safely handles missing or invalid odds.
    """
    permission_classes = [AllowAny]
    CACHE_TIMEOUT = 60  # seconds
    def get(self, request, *args, **kwargs):
        symbol = request.query_params.get("symbol")
        logger.info(f"[{timezone.now()}] 🔍 GroupedMarketView start for symbol={symbol}")
        if not symbol:
            return Response(
                {"detail": "symbol parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"market_grouped_{symbol}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # --- Fetch stock info ---
        try:
            stock = Stock.objects.only(
                "id", "symbol", "company_name", "url",
                "last_price", "last_change", "last_percent_change"
            ).get(symbol=symbol)
        except Stock.DoesNotExist:
            return Response(
                {"detail": f"Stock '{symbol}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        markets = Market.objects.filter(stock=stock, is_active=True).only(
            "id",
            "expiry_date",
            "target_price",
            "display_odds_over",
            "display_odds_under",
            "implied_odds_over",
            "implied_odds_under",
            "net_effective_nudge_over",
            "net_effective_nudge_under",
            "nudge_offset_over",
            "nudge_offset_under"
        )

        grouped = defaultdict(lambda: defaultdict(dict))

        for m in markets:
            expiry_str = m.expiry_date.strftime("%a, %d %b %Y")
            key = float(m.target_price or 0.0)

            # --- Convert safely ---
            def safe_decimal(display_odds):
                decimal_value = american_to_decimal_odds(display_odds)
                return round_two_places(decimal_value) if decimal_value else 0.0

            # --- Helper to structure each side ---
            def format_side(display, implied):
                """Returns consistent, rounded side structure."""
                decimal_val = safe_decimal(display)
                implied_rounded = round_two_places(implied) if implied is not None else 0.0
                fractional_val = american_to_fractional_odds(display)

                return {
                    "display_odds": display or "-",
                    "decimal": decimal_val,
                    "fractional": fractional_val,
                    "implied_odds": implied_rounded,
                }

            # --- Aggregate-level fields ---
            total_nudges = round_two_places(
                float(m.nudge_offset_over or 0.0) + float(m.nudge_offset_under or 0.0)
            )
            net_nudge = round_two_places(
                (float(m.net_effective_nudge_over or 0.0) + float(m.net_effective_nudge_under or 0.0))
            )

            grouped[expiry_str][key] = {
                "id": m.id,
                "is_active": m.is_active,
                "target_price": key,
                "net_nudge": net_nudge,          # ✅ per-market average effective nudge
                "total_nudges": total_nudges,    # ✅ combined nudge offsets for audit
                "over": format_side(
                    m.display_odds_over,
                    m.implied_odds_over,
                ),
                "under": format_side(
                    m.display_odds_under,
                    m.implied_odds_under,
                ),
            }

        response_data = {
            "stock": {
                "symbol": stock.symbol,
                "company_name": stock.company_name,
                "url": stock.url,
                "last_price": float(stock.last_price or 0.0),
                "last_change": float(stock.last_change or 0.0),
                "last_percent_change": stock.last_percent_change or "0%",
            },
            "grouped_markets": [
                {
                    "expiry_date": expiry,
                    "markets": [
                        grouped[expiry][tp] for tp in sorted(grouped[expiry].keys())
                    ],
                }
                for expiry in sorted(grouped.keys(), key=lambda x: datetime.strptime(x, "%a, %d %b %Y"))
            ],
        }

        cache.set(cache_key, response_data, self.CACHE_TIMEOUT)
        return Response(response_data, status=status.HTTP_200_OK)


# ✅ Auto-invalidate cache when a Market updates or deletes
@receiver([post_save, post_delete], sender=Market)
def invalidate_market_cache(sender, instance, **kwargs):
    if instance.stock and instance.stock.symbol:
        cache_key = f"market_grouped_{instance.stock.symbol}"
        cache.delete(cache_key)

class MarketStatusUpdateAPIView(APIView):
    """
    Toggles a market's is_active status and returns updated grouped data.
    """
    
    permission_classes = [AllowAny]

    # @transaction.atomic
    def patch(self, request, market_id):
        try:
            market = Market.objects.select_related("stock").get(id=market_id)
        except Market.DoesNotExist:
            return Response(
                {"detail": f"Market with id {market_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_active = request.data.get("is_active")
        market.is_active = bool(is_active) if is_active is not None else not market.is_active
        market.save(update_fields=["is_active"])

        symbol = market.stock.symbol
        cache.delete(f"market_grouped_{symbol}")

        grouped_data = get_grouped_market_data(symbol)
        if "status" in grouped_data and grouped_data["status"] == status.HTTP_404_NOT_FOUND:
            return Response(grouped_data, status=status.HTTP_404_NOT_FOUND)

        return Response(grouped_data, status=status.HTTP_200_OK)

class MarketOddsNudgeView(APIView):
    """
    Nudges a market's odds up or down the odds ladder or resets them.
    Returns updated grouped markets, stock info, total nudges count, and net nudge.
    """
    permission_classes = [AllowAny]

    # @transaction.atomic
    def post(self, request, market_id):
        try:
            market = Market.objects.select_related("stock").get(id=market_id)
        except Market.DoesNotExist:
            return Response(
                {"detail": f"Market with id {market_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        side = request.data.get("side")
        direction = request.data.get("direction")

        # --- Handle reset explicitly ---
        if side == "reset":
            market.reset_nudges()
            total_nudges = abs(market.nudge_offset_over) + abs(market.nudge_offset_under)
            net_nudge = market.nudge_offset_over - market.nudge_offset_under

            return Response(
                {
                    "status": "success",
                    "market_id": market.id,
                    "stock_symbol": market.stock.symbol,
                    "total_nudges": total_nudges,
                    "net_nudge": net_nudge,
                },
                status=status.HTTP_200_OK,
            )

        # --- Validate side/direction ---
        if side not in ["over", "under"]:
            return Response({"detail": "side must be either 'over' or 'under'."}, status=400)

        try:
            direction = int(direction)
        except (TypeError, ValueError):
            return Response({"detail": "direction must be an integer (+1 or -1)."}, status=400)

        if direction not in [-1, 1]:
            return Response({"detail": "direction must be +1 (up) or -1 (down)."}, status=400)

        try:
            # --- Apply nudge ---
            market = market.apply_nudge(
                side=side,
                direction=direction,
                user=request.user if request.user.is_authenticated else None,
            )

            # --- Fetch updated grouped data ---
            response_data = get_grouped_market_data(market.stock.symbol)

            if isinstance(response_data, dict) and "status" in response_data:
                return Response(response_data, status=response_data.get("status", 400))

            return Response(
                {
                    "status": "success",
                    "market_id": market.id,
                    "stock_symbol": market.stock.symbol,
                    "stock": response_data.get("stock", {}),
                    "grouped_markets": response_data.get("grouped_markets", []),
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as e:

            return Response(
                {
                    "detail": str(e),
                    "edge_case": True,
                    "market_id": market.id,
                    "stock_symbol": market.stock.symbol
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(f"Error in MarketOddsNudgeView: {e}", exc_info=True)
            return Response(
                {"detail": f"Unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class MarketOddsResetView(APIView):
    """
    Resets all manual nudges for a specific market back to its
    latest feed-based implied odds (baseline state).
    Clears nudge offsets and re-saves display odds from ladder.
    """
    permission_classes = [AllowAny]

    # @transaction.atomic
    def post(self, request, market_id):
        try:
            market = Market.objects.select_related("stock").get(id=market_id)
        except Market.DoesNotExist:
            return Response(
                {"detail": f"Market with id {market_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # --- 1. Reset nudge offsets ---
            market.reset_nudges()

            # --- 2. Choose the baseline implied odds ---
            def _valid_decimal(val):
                try:
                    dec = Decimal(val)
                    return dec if dec > 0 else None
                except Exception:
                    return None

            feed_over = _valid_decimal(getattr(market, "feed_implied_odds_over", None))
            feed_under = _valid_decimal(getattr(market, "feed_implied_odds_under", None))

            base_over = feed_over if feed_over is not None else _valid_decimal(market.implied_odds_over) or Decimal("0.50")
            base_under = feed_under if feed_under is not None else _valid_decimal(market.implied_odds_under) or Decimal("0.50")

            # --- 3. Update implied odds and br_true_percent ---
            market.implied_odds_over = base_over.quantize(Decimal("0.0001"))
            market.implied_odds_under = base_under.quantize(Decimal("0.0001"))

            market.br_true_percent_over = int(round(float(market.implied_odds_over) * 100))
            market.br_true_percent_under = int(round(float(market.implied_odds_under) * 100))

            # --- 4. Derive display (American) odds using ladder helper ---
            _, american_over = get_side_and_american_odds(market.implied_odds_over, ODDS_LADDER_JSON, vig=Decimal("9.0"))
            _, american_under = get_side_and_american_odds(market.implied_odds_under, ODDS_LADDER_JSON, vig=Decimal("9.0"))

            market.display_odds_over = str(american_over)
            market.display_odds_under = str(american_under)

            # --- 5. Persist updates ---
            market.save(update_fields=[
                "nudge_offset_over", "nudge_offset_under",
                "br_true_percent_over", "br_true_percent_under",
                "implied_odds_over", "implied_odds_under",
                "display_odds_over", "display_odds_under",
                "updated_at"
            ])

            # --- 7. Cache invalidation & fresh grouped payload ---
            cache.delete(f"market_grouped_{market.stock.symbol}")
            response_data = get_grouped_market_data(market.stock.symbol)

            if isinstance(response_data, dict) and "status" in response_data:
                return Response(response_data, status=response_data.get("status", 400))

            return Response(
                {
                    "status": "success",
                    "market_id": market.id,
                    "stock_symbol": market.stock.symbol,
                    "stock": response_data.get("stock", {}),
                    "grouped_markets": response_data.get("grouped_markets", []),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"detail": f"Error resetting nudges: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class StockMarketBulkResetView(APIView):
    """
    Resets all manual nudges for every Market under a given Stock symbol.
    Each market's odds are restored to their latest feed-based implied odds.
    Returns updated grouped markets and stock info.
    """
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request, symbol):
        # --- 1. Fetch stock ---
        try:
            stock = Stock.objects.get(symbol__iexact=symbol)
        except Stock.DoesNotExist:
            return Response(
                {"detail": f"Stock with symbol '{symbol}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # --- 2. Fetch all markets for this stock ---
        markets = Market.objects.filter(stock=stock)
        if not markets.exists():
            return Response(
                {"detail": f"No markets found for stock '{symbol}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reset_count = 0
        failed = []

        # --- 3. Reset each market ---
        for market in markets:
            try:
                # Reset offsets
                market.reset_nudges()

                # Restore base implied odds (prefer feed values)
                base_over = getattr(market, "feed_implied_odds_over", None) or market.implied_odds_over
                base_under = getattr(market, "feed_implied_odds_under", None) or market.implied_odds_under

                market.implied_odds_over = base_over
                market.implied_odds_under = base_under

                # Restore br_true_percent values
                market.br_true_percent_over = int(round(float(base_over) * 100))
                market.br_true_percent_under = int(round(float(base_under) * 100))

                # Recalculate display odds from ladder
                _, american_over = get_side_and_american_odds(base_over, ODDS_LADDER_JSON, vig=Decimal("9.0"))
                _, american_under = get_side_and_american_odds(base_under, ODDS_LADDER_JSON, vig=Decimal("9.0"))

                market.display_odds_over = str(american_over)
                market.display_odds_under = str(american_under)

                market.save(update_fields=[
                    "nudge_offset_over", "nudge_offset_under",
                    "br_true_percent_over", "br_true_percent_under",
                    "implied_odds_over", "implied_odds_under",
                    "display_odds_over", "display_odds_under",
                    "updated_at"
                ])

                reset_count += 1

            except Exception as e:
                failed.append({"id": market.id, "error": str(e)})

        # --- 4. Invalidate cache and fetch fresh grouped data ---
        cache.delete(f"market_grouped_{stock.symbol}")
        response_data = get_grouped_market_data(stock.symbol)

        # --- 5. Final response ---
        return Response(
            {
                "message": f"Reset completed for {reset_count} markets under {stock.symbol}.",
                "failed": failed,
                "grouped_markets": response_data.get("grouped_markets", []),
                "stock": response_data.get("stock", {}),
            },
            status=status.HTTP_200_OK,
        )
# def _apply_nudge_steps(start_br_true_percent: int, steps: int, odds_ladder: list, vig_key: str = "vig_9_0_percent"):
#     """
#     Apply `steps` (can be positive or negative) to the odds_ladder starting from
#     start_br_true_percent. Returns the final odds row dict (with br_true_percent,
#     br_true_percent_opposite, and american_odds) or None if we hit an invalid state.
#     This iteratively calls nudge_odds_ladder one step at a time to support multi-step offsets.
#     """
#     if steps == 0:
#         # return the current row if present
#         try:
#             row = next(r for r in odds_ladder if r["br_true_percent"] == start_br_true_percent)
#             # ensure vig_key present
#             if vig_key not in row:
#                 return None
#             return {
#                 "br_true_percent": row["br_true_percent"],
#                 "br_true_percent_opposite": row.get("br_true_percent_opposite"),
#                 "american_odds": row[vig_key],
#             }
#         except StopIteration:
#             return None

#     current_percent = start_br_true_percent
#     step_dir = 1 if steps > 0 else -1
#     for _ in range(abs(steps)):
#         result = nudge_odds_ladder(
#             current_br_true_percent=current_percent,
#             nudge_direction=step_dir,
#             odds_ladder=odds_ladder,
#             vig_key=vig_key,
#         )
#         if not result or "american_odds" not in result:
#             return None
#         # move to next base for subsequent step
#         current_percent = result["br_true_percent"]
#     return result



class StockRefreshView(APIView):
    """
    Simple API endpoint to refresh all stock price data.
    Uses each stock's get_current_price() method.
    """

    def get(self, request):
        api_key = getattr(settings, "ALPHA_VANTAGE_API_KEY", None)
        if not api_key:
            return Response(
                {"error": "Missing Alpha Vantage API key"},
                status=status.HTTP_400_BAD_REQUEST
            )
        for stock in Stock.objects.all():
            try:
                stock.get_current_price(api_key=api_key)
            except Exception as e:
                logger.error(f"Error refreshing price for {stock.symbol}: {e}")
                continue
        return Response(
            {"message": "Stock data refreshed successfully"},
            status=status.HTTP_200_OK
        )



class AdminMarketCreateAPIView(APIView):
    """
    Admin-only endpoint to create new betting markets.
    Expects a POST request with market details.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = MarketCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                market = serializer.save()
                message = f"Market '{market.stock.symbol} {market.outcome_type} ${market.target_price}' created successfully (ID: {market.id})."
                logger.info(message)
                return Response(
                    {
                        "message": message,
                        "market_id": market.id,
                        "market_details": {
                            "symbol": market.stock.symbol,
                            "target_price": str(market.target_price),
                            "expiry_date": market.expiry_date.strftime("%Y-%m-%d"),
                            "outcome_type": market.outcome_type,
                            "is_active": market.is_active,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                error_message = (
                    f"An unexpected error occurred during market creation: {e}"
                )
                logger.error(error_message, exc_info=True)
                return Response(
                    {"error": error_message},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminMarketUpdateOddsAPIView(APIView):
    """
    Admin-only endpoint to trigger the update of market odds.
    Can update odds for a specific market ID or for all active markets.
    Accepts an optional 'mock' boolean parameter in the request body.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        # Extract the 'mock' flag directly from request.data. Default to False.
        # This assumes 'mock' is a boolean in the JSON body, e.g., {"mock": true}
        use_mock = request.data.get("mock", False)

        serializer = MarketUpdateOddsSerializer(data=request.data)
        if serializer.is_valid():
            market_id = serializer.validated_data.get("market_id")

            # Build keyword arguments for call_command
            command_kwargs = {}
            if market_id:
                command_kwargs["market_id"] = market_id

            # Conditionally add the 'mock' argument if it's true
            if use_mock:
                command_kwargs["mock"] = (
                    True  # This will translate to --mock in the command
                )

            try:
                logger.info(
                    f"AdminMarketUpdateOddsAPIView: Calling update_market_odds with kwargs: {command_kwargs}"
                )
                call_command("update_market_odds", **command_kwargs)

                message = "Odds update initiated."
                if market_id:
                    message += f" For market ID: {market_id}."
                else:
                    message += " For all active markets."
                if use_mock:
                    message += " (Using mock Polygon data)."

                logger.info(message)
                return Response({"message": message}, status=status.HTTP_200_OK)
            except Exception as e:
                error_message = f"Failed to initiate odds update: {e}"
                logger.error(error_message, exc_info=True)
                return Response(
                    {"error": error_message},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from admin_panel.serializers import MarketCreateSerializer, MarketUpdateOddsSerializer, SuspendedMarketSerializer, SuspendedMarketUpdateSerializer


class SuspendedMarketsView(APIView):
    """List suspended markets. Admin-only."""
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        markets = (
            Market.objects.select_related("stock")
            .filter(Q(is_suspended_over=True) | Q(is_suspended_under=True))
            .order_by("stock__symbol", "expiry_date")
        )

        serializer = SuspendedMarketSerializer(markets, many=True)
        return Response({"suspended_markets": serializer.data}, status=status.HTTP_200_OK)


class SuspendedMarketDetailView(APIView):
    """Retrieve or update suspended state for a single market.

    PATCH body accepts any of: `is_active`, `is_suspended_over`, `is_suspended_under`, `requires_admin_override`.
    """
    permission_classes = [IsAdminUser]

    def get_object(self, market_id):
        try:
            return Market.objects.select_related("stock").get(id=market_id)
        except Market.DoesNotExist:
            return None

    def get(self, request, market_id, *args, **kwargs):
        market = self.get_object(market_id)
        if not market:
            return Response({"detail": "Market not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SuspendedMarketSerializer(market)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, market_id, *args, **kwargs):
        market = self.get_object(market_id)
        if not market:
            return Response({"detail": "Market not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SuspendedMarketUpdateSerializer(market, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        # Optionally clear grouped cache for the affected stock
        try:
            cache.delete(f"market_grouped_{market.stock.symbol}")
        except Exception:
            pass

        return Response(SuspendedMarketSerializer(market).data, status=status.HTTP_200_OK)
