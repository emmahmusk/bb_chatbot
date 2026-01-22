# market_data/views.py
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import logging
from datetime import timedelta
from django.utils.timezone import now
from django.core.cache import cache

from django.conf import settings
from django.db.models import Q, Count, Sum
import requests
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from mkt.alpha_vantage_data_fetcher import create_markets_from_options_data, populate_stocks
from .market_chart import ODDS_LADDER_JSON
from .alpha_vantage_utils import get_current_stock_price
from .utils import calculate_implied_probability_risk_neutral, fetch_alpha_vantage_options, get_side_and_american_odds
from .market_display_service import MarketDisplayService
from .odds_transformer import OddsCalculator
from .polygon_data_fetcher import PolygonDataFetcher
from django_q.tasks import async_task
from .models import OptionData
# from .tasks import ingest_live_options
from betengine.models import Bet, Market, Stock

logger = logging.getLogger(__name__)

# pagination.py

from rest_framework.pagination import PageNumberPagination

class OptionDataPagination(PageNumberPagination):
    page_size = 25  # default per page
    page_size_query_param = "page_size"
    max_page_size = 100

from .serializers import OptionDataSerializer

class OptionDataListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        symbol = request.query_params.get("symbol")
        expiration = request.query_params.get("expiration")  # YYYY-MM-DD
        strike = request.query_params.get("strike")  # Optional filter

        queryset = OptionData.objects.all()

        if symbol:
            queryset = queryset.filter(symbol__iexact=symbol)

        if expiration:
            queryset = queryset.filter(expiration=expiration)

        if strike:
            try:
                strike = float(strike)
                queryset = queryset.filter(strike=strike)
            except ValueError:
                return Response({"error": "Invalid strike price"}, status=400)

        queryset = queryset.order_by("-quote_date")

        paginator = OptionDataPagination()
        result_page = paginator.paginate_queryset(queryset, request)

        grouped = defaultdict(lambda: {"call": None, "put": None})

        for option in result_page:
            key = (option.symbol, option.expiration, option.strike, option.quote_date)
            option_data = OptionDataSerializer(option).data
            if option.option_type == "call":
                grouped[key]["call"] = option_data
            elif option.option_type == "put":
                grouped[key]["put"] = option_data

        nested_results = []
        for (symbol, expiration, strike, quote_date), pair in grouped.items():
            if pair["call"] and pair["put"]:
                nested_results.append({
                    "symbol": symbol,
                    "expiration": expiration,
                    "strike": strike,
                    "quote_date": quote_date,
                    "call": pair["call"],
                    "put": pair["put"]
                })

        return paginator.get_paginated_response(nested_results)

class PopulateStockAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        populate_stocks()
        return Response({"message": "Stocks populated successfully."})

class StockListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        stocks = Stock.objects.all().order_by("symbol")
        data = [
            {
                "symbol": stock.symbol,
                "company_name": stock.company_name,
                "url": stock.url,
            }
            for stock in stocks
        ]
        return Response(data)
    
ALPHA_VANTAGE_API_KEY = settings.ALPHA_VANTAGE_API_KEY
TOP_10_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "WMT", "UNH", "JPM"]
class TriggerOptionIngestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        symbols = request.data.get("symbols", [])
        date = request.data.get("highest_expiration", None)

        if not isinstance(symbols, list) or not symbols:
            return Response({"error": "Symbols must be a non-empty list."}, status=400)

        symbols = sorted({s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()})

        if not symbols:
            return Response({"error": "No valid symbols provided."}, status=400)

        # Prevent enqueuing another ingest while one is already running
        LOCK_KEY = "option_ingest_lock"
        lock_ttl = getattr(settings, "OPTION_INGEST_LOCK_TTL", 300)  # seconds
        
        if cache.get(LOCK_KEY):
            logger.info("Ingest job already running — not enqueuing another.")
            return Response({"message": "An ingest job is currently running. Try again later."}, status=202)
        
        # Set the lock right away
        cache.set(LOCK_KEY, True, timeout=lock_ttl)
        
        # Enqueue background task
        async_task("mkt.tasks.ingest_and_populate", symbols, settings.ALPHA_VANTAGE_API_KEY, date)
        
        return Response({
            "message": "Ingestion and population task started.",
            "symbols": symbols,
            "date": date,
        }, status=200)

# class TriggerOptionIngestView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def post(self, request):
#         symbols = request.data.get("symbols", [])
#         date = request.data.get("highest_expiration", None)
#         api_key = settings.ALPHA_VANTAGE_API_KEY

#         if not isinstance(symbols, list) or not symbols:
#             return Response({"error": "Symbols must be a non-empty list."}, status=400)

#         symbols = sorted({s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()})

#         if not symbols:
#             return Response({"error": "No valid symbols provided."}, status=400)

#         # Call the new async task that handles the full process
#         async_task("mkt.tasks.ingest_and_populate", symbols, api_key, date)

#         return Response({
#             "message": "Ingestion and population task started.",
#             "symbols": symbols,
#             "date": date,
#         }, status=200)
# class TriggerOptionIngestView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def post(self, request):
#         symbols = request.data.get("symbols", [])
#         date = request.data.get("highest_expiration", None)
#         api_key = settings.ALPHA_VANTAGE_API_KEY

#         if not isinstance(symbols, list) or not symbols:
#             return Response({"error": "Symbols must be a non-empty list."}, status=400)

#         # normalize: uppercase, strip, dedupe
#         symbols = sorted({s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()})

#         if not symbols:
#             return Response({"error": "No valid symbols provided."}, status=400)

#         processed_symbols = ingest_historical_options(symbols, api_key, date)
        
#         if processed_symbols:
#             stock_ids = list(Stock.objects.filter(symbol__in=processed_symbols).values_list('id', flat=True))
#             async_task("mkt.tasks.populate_market_for_stocks", stock_ids)
#         return Response({
#             "message": "Ingestion task started.",
#             "symbols": symbols,
#             "date": date,
#         }, status=200)




class PopulateMarketFromAlphaVantageAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        results = []
        for symbol in TOP_10_SYMBOLS:
            try:
                url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"

                r = requests.get(url)
                data = r.json()
                # print(f"\n📦 Raw response for {symbol}:")
                # print(json.dumps(data, indent=2))

                # print("Message:", data.get("message"))
                # print("Data Sample:", str(data.get("data")))

                if data.get("message") != "success":
                    results.append({symbol: f"❌ Error: {data.get('message', 'Unknown error')}"})
                    continue

                option_chain = data.get("data")
                try:
                    create_markets_from_options_data(symbol, option_chain)
                    results.append({symbol: f"✅ Processed {len(option_chain)} options"})
                except Exception as e:
                    results.append({symbol: f"⚠️ Error creating market for option: {str(e)}"})

            except Exception as e:
                results.append({symbol: f"❌ Failed to fetch or process: {str(e)}"})

        return Response({"results": results})

class AlphaVantageOptionsView(APIView):
    """
    API endpoint to fetch option contracts from Alpha Vantage for a given symbol and expiration date.
    """

    def get(self, request):
        symbol = request.query_params.get("symbol")
        expiration = request.query_params.get("expiration")  # 'YYYY-MM-DD'

        if not symbol:
            return Response({"error": "Missing 'symbol' query param"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            contracts = fetch_alpha_vantage_options(
                symbol=symbol,
                api_key=settings.ALPHA_VANTAGE_API_KEY,
                expiration_date=expiration
            )
            return Response(contracts, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarketDataAPIView(APIView):
    """
    API View to retrieve market listings for a specific expiry date.
    Responds with the first 10 market data entries.
    """

    def get(self, request, *args, **kwargs):
        # You might get expiry_date and stock_symbols from request.query_params
        # For this example, we'll use hardcoded values as in your example usage.
        # In a real application, you'd validate these parameters.

        chosen_expiry_str = request.query_params.get('expiry_date', '2025-07-19')
        try:
            chosen_expiry = datetime.strptime(chosen_expiry_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid expiry_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # In a real app, you might fetch these from a database or configuration
        common_stock_symbols = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOG", "AMZN", "GOOGL", "META", "NFLX", "AMD"] # Expanded for example

        try:
            # Initialize data fetcher and odds calculator
            # In a production setting, you might want to use dependency injection
            # or a singleton pattern for these services if they are costly to initialize.
            data_fetcher = PolygonDataFetcher()
            odds_calculator = OddsCalculator(vig=Decimal('0.10'), risk_free_rate=Decimal('0.02'))

            # Initialize the market display service
            market_service = MarketDisplayService(
                polygon_data_fetcher=data_fetcher,
                odds_calculator=odds_calculator
            )

            # Get the market list
            market_list = market_service.list_markets_by_expiry(
                expiry_date=chosen_expiry,
                stock_symbols=common_stock_symbols
            )

            # Respond with the first 10 data entries
            # If market_list has less than 10, it will return all available.
            return Response(market_list[:10], status=status.HTTP_200_OK)

        except ValueError as e:
            logger.exception(f"Configuration error in MarketDataAPIView: {e}")
            return Response(
                {"error": f"Configuration error: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.exception(f"An unexpected error occurred in MarketDataAPIView: {e}")
            return Response(
                {"error": "An unexpected error occurred while fetching market data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PopulateMarketFromOptionsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        symbol = request.query_params.get("symbol")
        expiration_param = request.query_params.get("expiration")  # Optional now

        if not symbol:
            return Response(
                {"error": "symbol query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            stock = Stock.objects.get(symbol__iexact=symbol)
        except Stock.DoesNotExist:
            return Response({"error": "Stock not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get latest stock price
        current_price = get_current_stock_price(symbol, api_key=settings.ALPHA_VANTAGE_API_KEY)
        if current_price == 0:
            return Response({"error": "Stock current price is 0 or missing."}, status=400)

        lower_bound = current_price * Decimal("0.85")
        upper_bound = current_price * Decimal("1.15")

        # Filter options
        if expiration_param:
            try:
                expiration_filter = datetime.strptime(expiration_param, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid expiration format. Use YYYY-MM-DD."}, status=400)
            option_qs = OptionData.objects.filter(
                symbol__iexact=stock.symbol,
                expiration=expiration_filter
            )
        else:
            today = datetime.now().date()
            option_qs = OptionData.objects.filter(
                symbol__iexact=stock.symbol,
                expiration__gte=today
            )

        if not option_qs.exists():
            return Response({"error": "No option contracts found for the given criteria."}, status=404)

        # Group by (symbol, expiration, strike)
        grouped = defaultdict(lambda: {"call": None, "put": None})
        for option in option_qs:
            key = (option.symbol, option.expiration, Decimal(option.strike))
            if option.option_type == "call":
                grouped[key]["call"] = option
            elif option.option_type == "put":
                grouped[key]["put"] = option

        markets_created = 0
        expirations_processed = set()

        for (symbol, expiration_date, strike), pair in grouped.items():
            call = pair.get("call")
            put = pair.get("put")
            if not (call and put):
                continue

            try:
                call_mark = Decimal(call.mark or 0)
                put_mark = Decimal(put.mark or 0)

                if call_mark <= 0 or put_mark <= 0:
                    continue

                if not (lower_bound <= strike <= upper_bound):
                    continue

                try:
                    p_over, p_under = calculate_implied_probability_risk_neutral(
                        call_mark=call_mark,
                        put_mark=put_mark
                    )
                except ValueError as e:
                    print(f"Skipping strike {strike} due to error: {e}")
                    continue

                if not (Decimal("0.45") <= p_over <= Decimal("0.55") and Decimal("0.45") <= p_under <= Decimal("0.55")):
                    continue

                first_side, first_american_odd = get_side_and_american_odds(
                    p_over, ODDS_LADDER_JSON, vig=Decimal("9.0")
                )
                second_side, second_american_odd = get_side_and_american_odds(
                    p_under, ODDS_LADDER_JSON, vig=Decimal("9.0")
                )

                display_odds = {
                    "over": first_american_odd,
                    "under": second_american_odd
                }

                ladder_favored_side = (
                    first_side.lower()
                    if first_american_odd <= second_american_odd
                    else second_side.lower()
                )

                option_volume_total = int(call.volume or 0) + int(put.volume or 0)

                bet_volume = (
                    Bet.objects.filter(
                        market__stock=stock,
                        market__target_price=strike,
                        market__expiry_date=expiration_date
                    )
                    .aggregate(total=Sum("amount_wagered"))["total"] or 0
                )

                total_volume = option_volume_total + (2 * int(bet_volume))
                if total_volume == 0:
                    continue

                # Create/update Over market
                Market.objects.update_or_create(
                    stock=stock,
                    target_price=strike,
                    expiry_date=expiration_date,
                    outcome_type="over",
                    defaults={
                        "implied_odds_over": p_over,
                        "implied_odds_under": p_under,
                        "display_odds_over": display_odds["over"],
                        "display_odds_under": display_odds["under"],
                        "ladder_favored_side": ladder_favored_side,
                        "total_volume": total_volume,
                        "is_active": True
                    }
                )

                # Create/update Under market
                # Market.objects.update_or_create(
                #     stock=stock,
                #     target_price=strike,
                #     expiry_date=expiration_date,
                #     outcome_type="under",
                #     defaults={
                #         "implied_odds_over": p_over,
                #         "implied_odds_under": p_under,
                #         "display_odds_over": display_odds["under"],
                #         "display_odds_under": display_odds["over"],
                #         "ladder_favored_side": ladder_favored_side,
                #         "total_volume": total_volume,
                #         "is_active": True
                #     }
                # )

                markets_created += 1
                expirations_processed.add(expiration_date)
            except Exception as e:
                print(f"Error processing strike {strike} for {symbol}: {e}")
                continue

        return Response({
            "message": f"{markets_created} markets created or updated.",
            "expirations_processed": sorted(list(expirations_processed))
        }, status=status.HTTP_201_CREATED)


class BulkPopulateMarketFromOptionsView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        stock_ids = list(Stock.objects.values_list("id", flat=True))

        # Enqueue one task per stock
        for stock_id in stock_ids:
            async_task("mkt.tasks.populate_market_for_stock", stock_id)

        return Response(
            {
                "message": f"Enqueued {len(stock_ids)} stock market population tasks",
                "task_count": len(stock_ids),
            },
            status=status.HTTP_202_ACCEPTED,
        )

FRESHNESS_THRESHOLD_SECONDS = 60


class LatestOptionDataView(APIView):
    """
    Return the most recent OptionData entries for a symbol.
    If data is stale or missing, auto-trigger background update.
    Example: /api/options/latest/?symbol=AAPL
    """

    def get(self, request):
        symbol = request.query_params.get("symbol")
        
        
        if not symbol:
            return Response(
                {"error": "symbol query param is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            latest_options = (
                OptionData.objects.filter(stock__symbol=symbol)
                .order_by("-updated_at")[:10]
            )

            if not latest_options.exists():
                # no options in DB → trigger ingestion
                async_task(
                    "markets.tasks.ingest_historical_options",
                    [symbol],
                    settings.ALPHA_VANTAGE_API_KEY,
                )
                return Response(
                    {
                        "symbol": symbol,
                        "options": [],
                        "message": "No data yet. Ingestion triggered.",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            # check freshness gap
            latest_market = (
                Market.objects.filter(stock__symbol=symbol)
                .order_by("-updated_at")
                .first()
            )
            latest_option = latest_options.first()

            freshness_gap = None
            auto_triggered = False
            if latest_market and latest_option:
                freshness_gap = abs(
                    (latest_market.updated_at - latest_option.updated_at).total_seconds()
                )
                if freshness_gap > FRESHNESS_THRESHOLD_SECONDS:
                    async_task(
                        "markets.tasks.ingest_historical_options",
                        [symbol],
                        settings.ALPHA_VANTAGE_API_KEY,
                    )
                    auto_triggered = True

            # data = [
            #     {
            #         "id": opt.id,
            #         "strike": opt.strike_price,
            #         "expiration": opt.expiration_date,
            #         "last_updated": opt.updated_at,
            #         "mark": opt.mark,
            #         "iv": opt.implied_volatility,
            #     }
            #     for opt in latest_options
            # ]

            return Response(
                {
                    "symbol": symbol,
                    "freshness_gap_seconds": freshness_gap,
                    "auto_triggered_background_update": auto_triggered,
                }
            )

        except Exception as e:
            logger.exception(f"[{symbol}] latest option fetch failed")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DataGapView(APIView):
    """
    Return time gap (in seconds) between latest Market update and OptionData update.
    Example: /api/options/gap/?symbol=AAPL
    """
    def get(self, request):
        symbol = request.query_params.get("symbol")
        if not symbol:
            return Response(
                {"error": "symbol query param is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        latest_market = (
            Market.objects.filter(stock__symbol=symbol).order_by("-updated_at").first()
        )
        latest_option = (
            OptionData.objects.filter(symbol=symbol)
            .order_by("-updated_at")
            .first()
        )

        if not latest_market or not latest_option:
            return Response(
                {"error": "Insufficient data"}, status=status.HTTP_404_NOT_FOUND
            )

        gap = abs(
            (latest_market.updated_at - latest_option.updated_at).total_seconds()
        )

        return Response(
            {
                "symbol": symbol,
                "market_last_updated": latest_market.updated_at,
                "option_last_updated": latest_option.updated_at,
                "gap_seconds": gap,
                "threshold_exceeded": gap > FRESHNESS_THRESHOLD_SECONDS,
            }
        )
class AggregatedDataGapView(APIView):
    """
    Return the average time gap (in seconds) between the latest Market update 
    and OptionData update across all stocks that actually have OptionData.
    Example: /api/options/gap/
    """

    def get(self, request):
        from django.db.models import Exists, OuterRef
        from betengine.models import Stock

        # Only consider stocks that have at least one OptionData
        stocks = Stock.objects.annotate(
            has_options=Exists(
                OptionData.objects.filter(symbol__iexact=OuterRef("symbol"))
            )
        ).filter(has_options=True)

        if not stocks.exists():
            return Response(
                {"error": "No stocks with OptionData available"},
                status=status.HTTP_404_NOT_FOUND,
            )

        gaps = []
        for stock in stocks:
            latest_market = (
                Market.objects.filter(stock=stock).order_by("-updated_at").first()
            )
            latest_option = (
                OptionData.objects.filter(symbol__iexact=stock.symbol)
                .order_by("-updated_at")
                .first()
            )

            if latest_market and latest_option:
                gap = abs(
                    (latest_market.updated_at - latest_option.updated_at).total_seconds()
                )
                gaps.append(gap)

        if not gaps:
            return Response(
                {"error": "Insufficient gap data for stocks with OptionData"},
                status=status.HTTP_404_NOT_FOUND,
            )

        avg_gap = sum(gaps) / len(gaps)

        return Response(
            {
                "stocks_checked": len(gaps),
                "average_gap_seconds": avg_gap,
                "threshold_exceeded": avg_gap > FRESHNESS_THRESHOLD_SECONDS,
            }
        )

class CleanOldOptionsView(APIView):
    """
    Deletes OptionData records where expiry_date < today + 6 days.
    """

    def delete(self, request):
        cutoff_date = now().date() + timedelta(days=6)

        deleted_count, _ = OptionData.objects.filter(expiration__lt=cutoff_date).delete()
        return Response(
            {"message": f"{deleted_count} expired options deleted."},
            status=status.HTTP_200_OK,
        )
# class BulkPopulateMarketFromOptionsView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def get(self, request, *args, **kwargs):
#         stocks = Stock.objects.all()
#         total_markets = 0
#         summary = {}
#         errors = {}

#         for stock in stocks:
#             try:
#                 # --- Fetch current price safely ---
#                 try:
#                     current_price = get_current_stock_price(
#                         stock.symbol,
#                         api_key=settings.ALPHA_VANTAGE_API_KEY
#                     )
#                 except Exception as e:
#                     logger.exception(f"[{stock.symbol}] Failed to fetch price")
#                     errors[stock.symbol] = f"Price fetch error: {str(e)}"
#                     continue

#                 if not current_price or current_price <= 0:
#                     logger.warning(f"[{stock.symbol}] Invalid current price: {current_price}")
#                     continue

#                 lower_bound = current_price * Decimal("0.85")
#                 upper_bound = current_price * Decimal("1.15")

#                 # --- Get options data safely ---
#                 today = datetime.now().date()
#                 try:
#                     option_qs = OptionData.objects.filter(
#                         symbol__iexact=stock.symbol,
#                         expiration__gte=today
#                     )
#                 except Exception as e:
#                     logger.exception(f"[{stock.symbol}] DB error fetching OptionData")
#                     errors[stock.symbol] = f"OptionData DB error: {str(e)}"
#                     continue

#                 if not option_qs.exists():
#                     continue

#                 # --- Group by strike & expiration ---
#                 grouped = defaultdict(lambda: {"call": None, "put": None})
#                 for option in option_qs:
#                     try:
#                         key = (option.symbol, option.expiration, Decimal(option.strike))
#                         grouped[key][option.option_type] = option
#                     except Exception as e:
#                         logger.warning(f"[{stock.symbol}] Invalid option data: {e}")
#                         continue

#                 markets_created = 0

#                 for (symbol, expiration_date, strike), pair in grouped.items():
#                     try:
#                         call, put = pair.get("call"), pair.get("put")
#                         if not (call and put):
#                             continue

#                         # Validate marks
#                         try:
#                             call_mark, put_mark = Decimal(call.mark or 0), Decimal(put.mark or 0)
#                         except Exception as e:
#                             logger.warning(f"[{stock.symbol}] Invalid mark for strike {strike}")
#                             continue

#                         if call_mark <= 0 or put_mark <= 0:
#                             continue
#                         if not (lower_bound <= strike <= upper_bound):
#                             continue

#                         # Probability calc
#                         try:
#                             p_over, p_under = calculate_implied_probability_risk_neutral(
#                                 call_mark=call_mark, put_mark=put_mark
#                             )
#                         except Exception as e:
#                             logger.warning(f"[{stock.symbol}] Probability calc error: {e}")
#                             continue

#                         if not (
#                             Decimal("0.10") <= p_over <= Decimal("0.90") and
#                             Decimal("0.10") <= p_under <= Decimal("0.90")
#                         ):
#                             continue

#                         # Odds calc
#                         try:
#                             first_side, first_american_odd = get_side_and_american_odds(
#                                 p_over, ODDS_LADDER_JSON, vig=Decimal("9.0")
#                             )
#                             second_side, second_american_odd = get_side_and_american_odds(
#                                 p_under, ODDS_LADDER_JSON, vig=Decimal("9.0")
#                             )
#                         except Exception as e:
#                             logger.warning(f"[{stock.symbol}] Odds calc failed: {e}")
#                             continue

#                         display_odds = {"over": first_american_odd, "under": second_american_odd}
#                         ladder_favored_side = (
#                             first_side.lower()
#                             if first_american_odd <= second_american_odd
#                             else second_side.lower()
#                         )

#                         # Volume calc
#                         try:
#                             option_volume_total = int(call.volume or 0) + int(put.volume or 0)
#                             bet_volume = (
#                                 Bet.objects.filter(
#                                     market__stock=stock,
#                                     market__target_price=strike,
#                                     market__expiry_date=expiration_date,
#                                 ).aggregate(total=Sum("amount_wagered"))["total"] or 0
#                             )
#                             total_volume = option_volume_total + (2 * int(bet_volume))
#                         except Exception as e:
#                             logger.exception(f"[{stock.symbol}] Volume query failed")
#                             continue

#                         if total_volume == 0:
#                             continue

#                         # --- Upsert Market ---
#                         try:
#                             with transaction.atomic():
#                                 Market.objects.update_or_create(
#                                     stock=stock,
#                                     target_price=strike,
#                                     expiry_date=expiration_date,
#                                     outcome_type="over",
#                                     defaults={
#                                         "implied_odds_over": p_over,
#                                         "implied_odds_under": p_under,
#                                         "display_odds_over": display_odds["over"],
#                                         "display_odds_under": display_odds["under"],
#                                         "ladder_favored_side": ladder_favored_side,
#                                         "total_volume": total_volume,
#                                         "is_active": True,
#                                     },
#                                 )
#                                 markets_created += 1
#                         except Exception as e:
#                             logger.exception(f"[{stock.symbol}] Market upsert failed")
#                             continue

#                     except Exception as inner_e:
#                         logger.exception(f"[{stock.symbol}] Unexpected error processing strike {strike}")
#                         continue

#                 if markets_created:
#                     summary[stock.symbol] = markets_created
#                     total_markets += markets_created

#             except Exception as e:
#                 logger.exception(f"[{stock.symbol}] Fatal error in stock loop")
#                 errors[stock.symbol] = str(e)
#                 continue

#         return Response(
#             {
#                 "message": f"{total_markets} markets created/updated",
#                 "breakdown": summary,
#                 "errors": errors,
#             },
#             status=status.HTTP_200_OK,
#         )


# class BulkPopulateMarketFromOptionsView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def get(self, request, *args, **kwargs):
#         stocks = Stock.objects.all()
#         total_markets = 0
#         summary = {}

#         for stock in stocks:
#             try:
#                 current_price = get_current_stock_price(
#                     stock.symbol,
#                     api_key=settings.ALPHA_VANTAGE_API_KEY
#                 )
#                 if current_price == 0:
#                     continue

#                 lower_bound = current_price * Decimal("0.85")
#                 upper_bound = current_price * Decimal("1.15")

#                 today = datetime.now().date()
#                 option_qs = OptionData.objects.filter(
#                     symbol__iexact=stock.symbol,
#                     expiration__gte=today
#                 )

#                 if not option_qs.exists():
#                     continue

#                 # Group (call/put pairing by strike & expiration)
#                 grouped = defaultdict(lambda: {"call": None, "put": None})
#                 for option in option_qs:
#                     key = (option.symbol, option.expiration, Decimal(option.strike))
#                     grouped[key][option.option_type] = option

#                 markets_created = 0
#                 for (symbol, expiration_date, strike), pair in grouped.items():
#                     call, put = pair.get("call"), pair.get("put")
#                     if not (call and put):
#                         continue

#                     call_mark, put_mark = Decimal(call.mark or 0), Decimal(put.mark or 0)
#                     if call_mark <= 0 or put_mark <= 0:
#                         continue
#                     if not (lower_bound <= strike <= upper_bound):
#                         continue

#                     try:
#                         p_over, p_under = calculate_implied_probability_risk_neutral(
#                             call_mark=call_mark, put_mark=put_mark
#                         )
#                     except ValueError:
#                         continue

#                     if not (Decimal("0.10") <= p_over <= Decimal("0.90") and Decimal("0.10") <= p_under <= Decimal("0.90")):
#                         continue

#                     first_side, first_american_odd = get_side_and_american_odds(
#                         p_over, ODDS_LADDER_JSON, vig=Decimal("9.0")
#                     )
#                     second_side, second_american_odd = get_side_and_american_odds(
#                         p_under, ODDS_LADDER_JSON, vig=Decimal("9.0")
#                     )

#                     display_odds = {"over": first_american_odd, "under": second_american_odd}
#                     ladder_favored_side = first_side.lower() if first_american_odd <= second_american_odd else second_side.lower()

#                     option_volume_total = int(call.volume or 0) + int(put.volume or 0)
#                     bet_volume = (
#                         Bet.objects.filter(
#                             market__stock=stock,
#                             market__target_price=strike,
#                             market__expiry_date=expiration_date,
#                         ).aggregate(total=Sum("amount_wagered"))["total"] or 0
#                     )
#                     total_volume = option_volume_total + (2 * int(bet_volume))
#                     if total_volume == 0:
#                         continue

#                     Market.objects.update_or_create(
#                         stock=stock,
#                         target_price=strike,
#                         expiry_date=expiration_date,
#                         outcome_type="over",
#                         defaults={
#                             "implied_odds_over": p_over,
#                             "implied_odds_under": p_under,
#                             "display_odds_over": display_odds["over"],
#                             "display_odds_under": display_odds["under"],
#                             "ladder_favored_side": ladder_favored_side,
#                             "total_volume": total_volume,
#                             "is_active": True,
#                         },
#                     )

#                     markets_created += 1

#                 if markets_created:
#                     summary[stock.symbol] = markets_created
#                     total_markets += markets_created

#             except Exception as e:
#                 print(f"Error processing stock {stock.symbol}: {e}")
#                 continue

#         return Response(
#             {"message": f"{total_markets} markets created/updated", "breakdown": summary},
#             status=status.HTTP_200_OK,
#         )

# class PopulateMarketFromOptionsView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def get(self, request, *args, **kwargs):
#         symbol = request.query_params.get("symbol")
#         expiration = request.query_params.get("expiration")

#         if not symbol or not expiration:
#             return Response(
#                 {"error": "symbol and expiration query parameters are required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             stock = Stock.objects.get(symbol__iexact=symbol)
#         except Stock.DoesNotExist:
#             return Response({"error": "Stock not found"}, status=status.HTTP_404_NOT_FOUND)

#         current_price = get_current_stock_price(symbol, api_key=settings.ALPHA_VANTAGE_API_KEY)
#         if current_price == 0:
#             return Response({"error": "Stock current price is 0 or missing."}, status=400)

#         lower_bound = current_price * Decimal("0.85")
#         upper_bound = current_price * Decimal("1.15")

#         option_qs = OptionData.objects.filter(
#             symbol__iexact=stock.symbol,
#             expiration=expiration,
#         )

#         grouped = defaultdict(lambda: {"call": None, "put": None})
#         for option in option_qs:
#             key = (option.symbol, option.expiration, Decimal(option.strike))
#             if option.option_type == "call":
#                 grouped[key]["call"] = option
#             elif option.option_type == "put":
#                 grouped[key]["put"] = option

#         markets_created = 0
#         for (symbol, expiration, strike), pair in grouped.items():
#             call = pair.get("call")
#             put = pair.get("put")
#             if not (call and put):
#                 continue

#             try:
#                 call_mark = Decimal(call.mark or 0)
#                 # call_ask = Decimal(call.ask or 0)
#                 put_mark = Decimal(put.mark or 0)
#                 # put_ask = Decimal(put.ask or 0)

#                 if not all([call_mark, put_mark]):
#                     continue

#                 if not (lower_bound <= strike <= upper_bound):
#                     continue

#                 # Calculate implied probabilities
#                 try:
#                     p_over, p_under = calculate_implied_probability_risk_neutral(
#                         call_mark=call_mark,
#                         put_mark=put_mark
#                     )
#                 except ValueError as e:
#                     print(f"Skipping strike {strike} due to error: {e}")
#                     continue

#                 # ✅ Only allow if both probabilities are near 50% (e.g., within ±5%)
#                 if not (Decimal("0.45") <= p_over <= Decimal("0.55") and Decimal("0.45") <= p_under <= Decimal("0.55")):
#                     print(f"Skipping strike {strike} due to unbalanced probabilities: Over={p_over}, Under={p_under}")
#                     continue

#                 # Apply vig and get American odds
#                 first_side, first_american_odd = get_side_and_american_odds(p_over, ODDS_LADDER_JSON, vig=Decimal("9.0"))
#                 second_side, second_american_odd = get_side_and_american_odds(p_under, ODDS_LADDER_JSON, vig=Decimal("9.0"))

#                 display_odds = {
#                     "over": first_american_odd,
#                     "under": second_american_odd
#                 }

#                 # Determine favored side based on odds ladder
#                 ladder_favored_side = first_side.lower() if first_american_odd <= second_american_odd else second_side.lower()

#                 # Compute bet volume manually (ensure market is queried if needed)
#                 # Get raw option contract volumes (default to 0 if missing)
#                 option_volume_call = int(call.volume or 0)
#                 option_volume_put = int(put.volume or 0)
#                 option_volume_total = option_volume_call + option_volume_put

#                 # Get total amount wagered on the market (bet volume)
#                 # Assuming expiration is a string like "2025-08-15"
#                 if isinstance(expiration, str):
#                     expiration = datetime.strptime(expiration, "%Y-%m-%d").date()

#                 bet_volume = (
#                     Bet.objects.filter(
#                         market__stock=stock,
#                         market__target_price=strike,
#                         market__expiry_date=expiration
#                     )
#                     .aggregate(total=Sum("amount_wagered"))["total"] or 0
#                 )
#                 # Hybrid trending volume score — weigh bet volume more heavily if desired
#                 total_volume = option_volume_total + (2 * int(bet_volume))


#                 if total_volume == 0:
#                     continue

#                 # Save Over market
#                 Market.objects.update_or_create(
#                     stock=stock,
#                     target_price=strike,
#                     expiry_date=expiration,
#                     outcome_type="over",
#                     defaults={
#                         "implied_odds_over": p_over,
#                         "implied_odds_under": p_under,
#                         "display_odds_over": display_odds["over"],
#                         "display_odds_under": display_odds["under"],
#                         "ladder_favored_side": ladder_favored_side,
#                         "total_volume": total_volume,
#                         "is_active": True
#                     }
#                 )

#                 # Save Under market
#                 Market.objects.update_or_create(
#                     stock=stock,
#                     target_price=strike,
#                     expiry_date=expiration,
#                     outcome_type="under",
#                     defaults={
#                         "implied_odds_over": p_over,
#                         "implied_odds_under": p_under,
#                         "display_odds_over": display_odds["under"],
#                         "display_odds_under": display_odds["over"],
#                         "ladder_favored_side": ladder_favored_side,
#                         "total_volume": total_volume,
#                         "is_active": True
#                     }
#                 )

#                 markets_created += 2

#             except Exception as e:
#                 print(f"Error processing strike {strike} for {symbol}: {e}")
#                 continue

#         return Response({
#             "message": f"{markets_created} markets created or updated for {symbol} {expiration}."
#         }, status=status.HTTP_201_CREATED)



# class PopulateMarketFromOptionsView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def get(self, request, *args, **kwargs):
#         symbol = request.query_params.get("symbol")
#         expiration = request.query_params.get("expiration")

#         if not symbol or not expiration:
#             return Response(
#                 {"error": "symbol and expiration query parameters are required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             stock = Stock.objects.get(symbol__iexact=symbol)
#         except Stock.DoesNotExist:
#             return Response({"error": "Stock not found"}, status=status.HTTP_404_NOT_FOUND)

#         current_price = get_current_stock_price(symbol, api_key=settings.ALPHA_VANTAGE_API_KEY)
#         if current_price == 0:
#             return Response({"error": "Stock current price is 0 or missing."}, status=400)

#         lower_bound = current_price * Decimal("0.85")
#         upper_bound = current_price * Decimal("1.15")

#         option_qs = OptionData.objects.filter(
#             symbol__iexact=stock.symbol,
#             expiration=expiration,
#         )

#         grouped = defaultdict(lambda: {"call": None, "put": None})
#         for option in option_qs:
#             key = (option.symbol, option.expiration, Decimal(option.strike))
#             if option.option_type == "call":
#                 grouped[key]["call"] = option
#             elif option.option_type == "put":
#                 grouped[key]["put"] = option

#         markets_created = 0
#         for (symbol, expiration, strike), pair in grouped.items():
#             call = pair.get("call")
#             put = pair.get("put")
#             if not (call and put):
#                 continue

#             try:
#                 call_bid = Decimal(call.bid or 0)
#                 call_ask = Decimal(call.ask or 0)
#                 put_bid = Decimal(put.bid or 0)
#                 put_ask = Decimal(put.ask or 0)

#                 if not all([call_bid, call_ask, put_bid, put_ask]):
#                     continue

#                 if not (lower_bound <= strike <= upper_bound):
#                     continue

#                 # 👇 Use new midprice ratio model
#                 try:
#                     p_over, p_under = calculate_implied_probability_risk_neutral(
#                         call_bid=call_bid,
#                         call_ask=call_ask,
#                         put_bid=put_bid,
#                         put_ask=put_ask
#                     )
#                 except ValueError as e:
#                     print(f"Skipping strike {strike} due to error: {e}")
#                     continue
#                 # Apply vig and Convert to American odds
#                 first_side, first_american_odd = get_side_and_american_odds(p_over, ODDS_LADDER_JSON, vig=Decimal("9.0"))
#                 second_side, second_american_odd = get_side_and_american_odds(p_under, ODDS_LADDER_JSON, vig=Decimal("9.0"))
           

#                 # Assign odds to correct buckets
#                 display_odds = {
#                     "over": first_american_odd if first_side.lower() == "over" else second_american_odd,
#                     "under": second_american_odd if second_side.lower() == "under" else first_american_odd,
#                 }
#                 # Save Over market
#                 Market.objects.update_or_create(
#                     stock=stock,
#                     target_price=strike,
#                     expiry_date=expiration,
#                     outcome_type="over",
#                     defaults={
#                         "implied_odds_over": p_over,
#                         "implied_odds_under": p_under,
#                         "display_odds_over": display_odds["over"],
#                         "display_odds_under": display_odds["under"],
#                         "is_active": True
#                     }
#                 )

#                 # Save Under market
#                 Market.objects.update_or_create(
#                     stock=stock,
#                     target_price=strike,
#                     expiry_date=expiration,
#                     outcome_type="under",
#                     defaults={
#                         "implied_odds_over": p_over,
#                         "implied_odds_under": p_under,
#                         "display_odds_over": display_odds["under"],
#                         "display_odds_under": display_odds["over"],
#                         "is_active": True
#                     }
#                 )

#                 markets_created += 2

#             except Exception as e:
#                 print(f"Error processing strike {strike} for {symbol}: {e}")
#                 continue

#         return Response({
#             "message": f"{markets_created} markets created or updated for {symbol} {expiration}."
#         }, status=status.HTTP_201_CREATED)







# class PopulateStocksAPIView(APIView):
#     """
#     API View to trigger the population of the Stock model from Polygon.io.
#     This endpoint is designed for initial setup/testing and is intentionally
#     unauthenticated for ease of use in Sprint 1.
#     """

#     # For Sprint 1, no authentication or permissions for simplicity.
#     # In production, strongly consider adding:
#     # authentication_classes = [SessionAuthentication, TokenAuthentication] # Or JWT
#     # permission_classes = [IsAdminUser] # Or a custom permission for admin roles
#     def get(self, request, *args, **kwargs):
#         """
#         Return a paginated list of supported stocks, optionally filtered by search.
#         Query Params:
#         - search: keyword to search symbol or company_name
#         - ordering: symbol or company_name (prefix with '-' for descending)
#         - page, page_size: pagination controls
#         """
#         search_query = request.GET.get("search", "")
#         ordering = request.GET.get("ordering", "symbol")  # default sort

#         try:
#             stocks = Stock.objects.all()

#             if search_query:
#                 stocks = stocks.filter(
#                     Q(symbol__icontains=search_query)
#                     | Q(company_name__icontains=search_query)
#                 )

#             if ordering:
#                 stocks = stocks.order_by(ordering)

#             # Paginate the result
#             paginator = PageNumberPagination()
#             paginator.page_size = request.GET.get("page_size", 20)
#             paginated_stocks = paginator.paginate_queryset(stocks, request)

#             serializer = StockSerializer(paginated_stocks, many=True)
#             logger.info(
#                 f"GET /stocks - Returned {len(serializer.data)} stocks (search: {search_query})"
#             )
#             return paginator.get_paginated_response(serializer.data)

#         except Exception as e:
#             logger.error(f"Error fetching stocks: {str(e)}", exc_info=True)
#             return Response(
#                 {"status": "error", "message": "Failed to retrieve stocks."},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#     def post(self, request, *args, **kwargs):
#         api_key = settings.POLYGON_API_KEY
#         if not api_key:
#             logger.error("POLYGON_API_KEY environment variable not set in settings.")
#             return Response(
#                 {
#                     "status": "error",
#                     "message": "Server configuration error: Polygon API key not set.",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         client = RESTClient(api_key)

#         # You can allow the client to specify limits or common types, or keep it fixed
#         # For simplicity, we'll use fixed parameters for now.
#         # Max limit per request is 1000 in Polygon.io's list_tickers.
#         # For a full initial sync, you'd likely need to handle pagination (next_url).
#         # For this API endpoint, we'll aim for a reasonable first batch.
#         limit = request.data.get("limit", 50)
#         refresh_all = request.data.get("refresh_all", False)
#         market = request.data.get("market", "stocks")
#         active = request.data.get("active", True)
#         sort = request.data.get("sort", "ticker")
#         order = request.data.get("order", "asc")

#         # Define the supported ticker types for "equity-only betting"
#         # You might want to make this configurable in settings or via request params
#         supported_ticker_types = [
#             "CS",
#             "ADRC",
#         ]  # Common Stock, American Depository Receipt Common

#         tickers_processed = 0
#         tickers_created = 0
#         errors = []

#         logger.info(
#             f"API request to populate stocks received. Limit: {limit}, Refresh All: {refresh_all}"
#         )

#         try:
#             # Note: For very large datasets beyond 'limit', you'd need to paginate
#             # and make multiple requests using the 'next_url'. For an initial bulk,
#             # this single call with a reasonable limit is often sufficient.
#             ticker_iterator = client.list_tickers(
#                 market=market,
#                 active=active,
#                 order=order,
#                 limit=limit,
#                 sort=sort,
#                 type=",".join(supported_ticker_types),  # Filter by types here
#             )

#             for ticker_data in ticker_iterator:
#                 # Type check to ensure data conforms to expected PolygonTicker model
#                 if not isinstance(ticker_data, PolygonTicker):
#                     logger.warning(
#                         f"Received unexpected ticker data format: {ticker_data}"
#                     )
#                     errors.append(f"Skipped invalid ticker data format: {ticker_data}")
#                     continue

#                 # Edge Case: Ensure essential fields are present
#                 if not ticker_data.ticker or not ticker_data.name:
#                     logger.warning(
#                         f"Skipping ticker with missing symbol or name: {ticker_data}"
#                     )
#                     errors.append(
#                         f"Skipped ticker with missing symbol or name: {ticker_data.ticker or 'N/A'}"
#                     )
#                     continue

#                 try:
#                     with transaction.atomic():
#                         stock_obj, created = Stock.objects.update_or_create(
#                             symbol=ticker_data.ticker,
#                             defaults={
#                                 "company_name": ticker_data.name,
#                                 # You can add other fields from ticker_data if your Stock model
#                                 # has them (e.g., primary_exchange, locale, type, currency_name)
#                             },
#                         )
#                         if created:
#                             tickers_created += 1
#                             logger.info(
#                                 f"Created new Stock: {stock_obj.symbol} ({stock_obj.company_name})"
#                             )
#                         elif refresh_all:
#                             logger.debug(f"Updated existing Stock: {stock_obj.symbol}")

#                         tickers_processed += 1

#                 except Exception as db_error:
#                     logger.error(
#                         f"Database error storing stock {ticker_data.ticker}: {db_error}",
#                         exc_info=True,
#                     )
#                     errors.append(f"DB error for {ticker_data.ticker}: {str(db_error)}")

#         except Exception as polygon_error:
#             logger.error(
#                 f"Error fetching tickers from Polygon.io: {polygon_error}",
#                 exc_info=True,
#             )
#             return Response(
#                 {
#                     "status": "error",
#                     "message": f"Failed to fetch data from Polygon.io: {str(polygon_error)}",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         response_message = f"Stock population process completed. Processed {tickers_processed} tickers. Created {tickers_created} new tickers."
#         if errors:
#             response_message += f" Encountered {len(errors)} errors/warnings."
#             return Response(
#                 {"status": "warning", "message": response_message, "errors": errors},
#                 status=status.HTTP_200_OK,  # Still OK, but with warnings
#             )
#         else:
#             return Response(
#                 {"status": "success", "message": response_message},
#                 status=status.HTTP_200_OK,
#             )



# class GenerateMarketsFromOptionsView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def post(self, request, *args, **kwargs):
#         """
#         This view takes OptionData (calls and puts), calculates implied odds with vig,
#         and creates or updates Market objects for both over and under scenarios.
#         """
#         symbol = request.data.get("symbol")
#         expiration = request.data.get("expiration")  # Format: 'YYYY-MM-DD'
#         vig = Decimal("0.09")  # You can make this configurable

#         if not symbol or not expiration:
#             return Response({"error": "symbol and expiration are required."}, status=400)

#         stock = Stock.objects.filter(symbol__iexact=symbol).first()
#         if not stock:
#             return Response({"error": f"Stock {symbol} not found."}, status=404)

#         try:
#             current_price = Decimal(stock.last_price)
#         except (TypeError, InvalidOperation):
#             return Response({"error": "Invalid or missing current stock price."}, status=400)

#         threshold = Decimal("0.15")  # 15% range up/down
#         min_strike = current_price * (1 - threshold)
#         max_strike = current_price * (1 + threshold)

#         options = OptionData.objects.filter(symbol=symbol, expiration=expiration)
#         grouped = defaultdict(lambda: {"call": None, "put": None})

#         for option in options:
#             try:
#                 strike = Decimal(option.strike)
#             except (TypeError, InvalidOperation):
#                 continue

#             if not (min_strike <= strike <= max_strike):
#                 continue  # Filter: skip strikes too far from current price

#             key = (option.strike, option.quote_date)
#             if option.option_type == "call":
#                 grouped[key]["call"] = option
#             elif option.option_type == "put":
#                 grouped[key]["put"] = option

#         created, updated, skipped = 0, 0, 0

#         for (strike, quote_date), pair in grouped.items():
#             call = pair["call"]
#             put = pair["put"]

#             if not call or not put:
#                 skipped += 1
#                 continue

#             try:
#                 p_over = calculate_implied_probability_from_options(call.mark_price, put.mark_price, strike)
# #                 p_under = Decimal("1.0") - p_over
#                 call_prob = calculate_implied_probability(call.mark)
#                 put_prob = calculate_implied_probability(put.mark)

#                 adj_call_prob, adj_put_prob = apply_vig(call_prob, put_prob, vig)

#                 call_american = probability_to_american_odds(adj_call_prob)
#                 put_american = probability_to_american_odds(adj_put_prob)

#                 over_obj, created_over = Market.objects.update_or_create(
#                     stock=stock,
#                     target_price=Decimal(strike),
#                     expiry_date=parse_date(expiration),
#                     outcome_type="over",
#                     defaults={
#                         "implied_odds_over": adj_call_prob,
#                         "implied_odds_under": adj_put_prob,
#                         "display_odds_over": call_american,
#                         "display_odds_under": put_american,
#                         "is_active": True
#                     }
#                 )

#                 under_obj, created_under = Market.objects.update_or_create(
#                     stock=stock,
#                     target_price=Decimal(strike),
#                     expiry_date=parse_date(expiration),
#                     outcome_type="under",
#                     defaults={
#                         "implied_odds_over": adj_put_prob,
#                         "implied_odds_under": adj_call_prob,
#                         "display_odds_over": put_american,
#                         "display_odds_under": call_american,
#                         "is_active": True
#                     }
#                 )

#                 if created_over or created_under:
#                     created += 2
#                 else:
#                     updated += 2

#             except Exception as e:
#                 print(f"❌ Error processing strike {strike} for {symbol}: {e}")
#                 skipped += 1
#                 continue

#         return Response({
#             "message": "Market generation completed.",
#             "stock": symbol,
#             "expiration": expiration,
#             "created": created,
#             "updated": updated,
#             "skipped_pairs": skipped
#         })
