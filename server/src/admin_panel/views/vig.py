# betting/views/admin/vig.py
from collections import defaultdict
import logging

from django.db import transaction
from django.utils import timezone

from rest_framework import permissions, status
from decimal import Decimal

from mkt.models import OptionData
from betengine.models import Stock, Market

from mkt.alpha_vantage_utils import get_current_stock_price
from mkt.utils import (calculate_implied_probability_risk_neutral, get_american_odds_from_ladder, get_side_and_american_odds)

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from admin_panel.serializers import MarketVigAdjustmentSerializer
from betengine.serializers import MarketSerializer
from betengine.utils import apply_vig, convert_decimal_to_american_odds

from mkt.market_chart import ODDS_LADDER_JSON


logger = logging.getLogger(__name__)

class OverrideVigView(APIView):
    permission_classes = [permissions.AllowAny]  # Change to IsAdminUser in production

    def post(self, request, *args, **kwargs):
        market_id = request.data.get("market_id")
        vig_percent = request.data.get("vig_percent")

        if not market_id or vig_percent is None:
            return Response({"error": "market_id and vig_percent are required."}, status=400)

        try:
            vig_percent = Decimal(vig_percent)
        except:
            return Response({"error": "vig_percent must be a valid decimal."}, status=400)

        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return Response({"error": "Market not found."}, status=404)

        stock = market.stock
        strike = market.target_price
        expiration = market.expiry_date

        option_qs = OptionData.objects.filter(
            symbol__iexact=stock.symbol,
            expiration=expiration,
            strike=strike
        )

        call = option_qs.filter(option_type="call").first()
        put = option_qs.filter(option_type="put").first()

        if not call or not put:
            return Response({"error": "Both call and put options required."}, status=400)

        try:
            call_mark = Decimal(call.mark or 0)
            put_mark = Decimal(put.mark or 0)

            if not all([call_mark, put_mark]):
                return Response({"error": "Missing call_mark/put_mark values for call or put."}, status=400)

            # Calculate probabilities
            p_over, p_under = calculate_implied_probability_risk_neutral(
                call_mark=call_mark,
                put_mark=put_mark
            )

            # Convert with new vig
            first_side, first_american_odd = get_side_and_american_odds(p_over, ODDS_LADDER_JSON, vig=vig_percent)
            second_side, second_american_odd = get_side_and_american_odds(p_under, ODDS_LADDER_JSON, vig=vig_percent)

            display_odds = {
                "over": first_american_odd,
                "under": second_american_odd,
            }

            # Update both markets
            Market.objects.update_or_create(
                stock=stock,
                target_price=strike,
                expiry_date=expiration,
                outcome_type="over",
                defaults={
                    "implied_odds_over": p_over,
                    "implied_odds_under": p_under,
                    "display_odds_over": display_odds["over"],
                    "display_odds_under": display_odds["under"],
                    "is_active": True
                }
            )

            return Response({
                "status": "success",
                "message": f"Vig updated to {vig_percent}% for market ID {market_id}"
            }, status=200)

        except Exception as e:
            return Response({"status": "failed", "error": str(e)}, status=500)
        
class AdminNudgeOdds(APIView):
    permission_classes = [permissions.AllowAny]  # Change to IsAdminUser in production

    def post(self, request, *args, **kwargs):
        market_id = request.data.get("market_id")
        
        if not market_id or vig_percent is None:
            return Response({"error": "market_id and vig_percent are required."}, status=400)

        try:
            vig_percent = Decimal(vig_percent)
        except:
            return Response({"error": "vig_percent must be a valid decimal."}, status=400)

        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return Response({"error": "Market not found."}, status=404)

        stock = market.stock
        strike = market.target_price
        expiration = market.expiry_date

        option_qs = OptionData.objects.filter(
            symbol__iexact=stock.symbol,
            expiration=expiration,
            strike=strike
        )

        call = option_qs.filter(option_type="call").first()
        put = option_qs.filter(option_type="put").first()

        if not call or not put:
            return Response({"error": "Both call and put options required."}, status=400)

        try:
            call_mark = Decimal(call.mark or 0)
            put_mark = Decimal(put.mark or 0)

            if not all([call_mark, put_mark]):
                return Response({"error": "Missing call_mark/put_mark values for call or put."}, status=400)

            # Calculate probabilities
            p_over, p_under = calculate_implied_probability_risk_neutral(
                call_mark=call_mark,
                put_mark=put_mark
            )

            # Convert with new vig
            first_side, first_american_odd = get_side_and_american_odds(p_over, ODDS_LADDER_JSON, vig=vig_percent)
            second_side, second_american_odd = get_side_and_american_odds(p_under, ODDS_LADDER_JSON, vig=vig_percent)

            display_odds = {
                "over": first_american_odd,
                "under": second_american_odd,
            }

            # Update both markets
            Market.objects.update_or_create(
                stock=stock,
                target_price=strike,
                expiry_date=expiration,
                outcome_type="over",
                defaults={
                    "implied_odds_over": p_over,
                    "implied_odds_under": p_under,
                    "display_odds_over": display_odds["over"],
                    "display_odds_under": display_odds["under"],
                    "is_active": True
                }
            )

            return Response({
                "status": "success",
                "message": f"Vig updated to {vig_percent}% for market ID {market_id}"
            }, status=200)

        except Exception as e:
            return Response({"status": "failed", "error": str(e)}, status=500)
class BulkOverrideVigByIdsView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        market_ids = request.data.get("market_ids", [])
        vig_percent = request.data.get("vig_percent")

        if not market_ids or vig_percent is None:
            return Response(
                {"error": "market_ids (list) and vig_percent are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # parse vig
        try:
            vig_percent = Decimal(vig_percent)
        except:
            return Response(
                {"error": "vig_percent must be a valid decimal."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # fetch markets
        markets = Market.objects.filter(id__in=market_ids)
        if not markets.exists():
            return Response(
                {"error": "No markets found for the given IDs."},
                status=status.HTTP_404_NOT_FOUND
            )

        updated = 0

        for market in markets:
            stock   = market.stock
            strike  = market.target_price
            expiry  = market.expiry_date

            # grab call & put option data
            opts = OptionData.objects.filter(
                symbol__iexact=stock.symbol,
                strike=strike,
                expiration=expiry
            )
            call = opts.filter(option_type="call").first()
            put  = opts.filter(option_type="put").first()
            if not (call and put):
                continue

            # bids and asks
            try:
                cm = Decimal(call.mark or 0)
                pm = Decimal(put.mark  or 0)
                if not all([cm, pm]):
                    continue
            except:
                continue

            # recalc probabilities
            try:
                p_over, p_under = calculate_implied_probability_risk_neutral(call_mark=cm, put_mark=pm)
            except ValueError:
                continue

            # recalc american odds with new vig
            _, odd_over = get_side_and_american_odds(p_over, ODDS_LADDER_JSON, vig=vig_percent)
            _, odd_under = get_side_and_american_odds(p_under, ODDS_LADDER_JSON, vig=vig_percent)

            # update this market record
            market.implied_odds_over   = p_over
            market.implied_odds_under  = p_under
            if market.outcome_type == "over":
                market.display_odds_over  = odd_over
                market.display_odds_under = odd_under
            # else:  # "under"
            #     market.display_odds_over  = odd_under
            #     market.display_odds_under = odd_over

            market.is_active = True
            market.save()
            updated += 1

        return Response(
            {"message": f"{updated} market(s) updated with vig={vig_percent}%."},
            status=status.HTTP_200_OK
        )

# class OverrideVigView(APIView):
#     permission_classes = [permissions.AllowAny]  # Ensure only admin can access

#     def post(self, request, *args, **kwargs):
#         symbol = request.data.get("symbol")
#         expiration = request.data.get("expiration")
#         strike = request.data.get("strike")
#         vig_percent = request.data.get("vig_percent")

#         if not all([symbol, expiration, strike, vig_percent]):
#             return Response({"error": "symbol, expiration, strike, and vig_percent are required."}, status=400)

#         try:
#             vig_percent = Decimal(vig_percent)
#             strike = Decimal(strike)
#         except:
#             return Response({"error": "vig_percent and strike must be valid decimals."}, status=400)

#         try:
#             stock = Stock.objects.get(symbol__iexact=symbol)
#         except Stock.DoesNotExist:
#             return Response({"error": "Stock not found."}, status=404)

#         option_qs = OptionData.objects.filter(
#             symbol__iexact=stock.symbol,
#             expiration=expiration,
#             strike=strike
#         )

#         call = option_qs.filter(option_type="call").first()
#         put = option_qs.filter(option_type="put").first()

#         if not call or not put:
#             return Response({"error": "Both call and put options are required for the given strike."}, status=400)

#         try:
#             call_bid = Decimal(call.bid or 0)
#             call_ask = Decimal(call.ask or 0)
#             put_bid = Decimal(put.bid or 0)
#             put_ask = Decimal(put.ask or 0)

#             if not all([call_bid, call_ask, put_bid, put_ask]):
#                 return Response({"error": "Missing bid/ask values for call or put."}, status=400)

#             p_over, p_under = calculate_implied_probability_risk_neutral(
#                 call_bid=call_bid,
#                 call_ask=call_ask,
#                 put_bid=put_bid,
#                 put_ask=put_ask
#             )

#             # over_american = get_american_odds_from_ladder(p_over, ODDS_LADDER_JSON, side="home", vig_percent=vig_percent)
#             # under_american = get_american_odds_from_ladder(p_under, ODDS_LADDER_JSON, side="away", vig_percent=vig_percent)

#             # Apply vig and Convert to American odds
#             first_side, first_american_odd = get_side_and_american_odds(p_over, ODDS_LADDER_JSON, vig=vig_percent)
#             second_side, second_american_odd = get_side_and_american_odds(p_under, ODDS_LADDER_JSON, vig=vig_percent)
        

#             # Assign odds to correct buckets
#             display_odds = {
#                 "over": first_american_odd,
#                 "under": second_american_odd,
#             }

#             # Update Over market
#             Market.objects.update_or_create(
#                 stock=stock,
#                 target_price=strike,
#                 expiry_date=expiration,
#                 outcome_type="over",
#                 defaults={
#                     "implied_odds_over": p_over,
#                     "implied_odds_under": p_under,
#                     "display_odds_over": display_odds["over"],
#                     "display_odds_under": display_odds["under"],
#                     "is_active": True
#                 }
#             )

#             # Update Under market
#             Market.objects.update_or_create(
#                 stock=stock,
#                 target_price=strike,
#                 expiry_date=expiration,
#                 outcome_type="under",
#                 defaults={
#                     "implied_odds_over": p_over,
#                     "implied_odds_under": p_under,
#                     "display_odds_over": display_odds["under"],
#                     "display_odds_under": display_odds ["over"],
#                     "is_active": True
#                 }
#             )

#             return Response({
#                 "status": "success",
#                 "message": f"Vig successfully overridden to {vig_percent}% for {symbol} {expiration} @ {strike}."
#             }, status=200)

#         except Exception as e:
#             return Response({"status": "failed", "error": f"Unexpected error: {e}"}, status=500)

# class BulkOverrideVigView(APIView):
#     permission_classes = [permissions.IsAdminUser]

#     def post(self, request, *args, **kwargs):
#         symbol = request.data.get("symbol")
#         expiration = request.data.get("expiration")
#         strike_prices = request.data.get("strike_prices", [])  # Optional
#         vig_percent = request.data.get("vig_percent")

#         if not all([symbol, expiration, vig_percent]):
#             return Response({"error": "symbol, expiration, and vig_percent are required."}, status=400)

#         try:
#             vig_percent = Decimal(vig_percent)
#         except:
#             return Response({"error": "vig_percent must be a valid decimal."}, status=400)

#         try:
#             stock = Stock.objects.get(symbol__iexact=symbol)
#         except Stock.DoesNotExist:
#             return Response({"error": "Stock not found."}, status=404)

#         # Filter by symbol and expiration
#         option_qs = OptionData.objects.filter(
#             symbol__iexact=stock.symbol,
#             expiration=expiration
#         )

#         if strike_prices:
#             try:
#                 strike_prices = [Decimal(sp) for sp in strike_prices]
#             except:
#                 return Response({"error": "All strike_prices must be valid decimals."}, status=400)
#             option_qs = option_qs.filter(strike__in=strike_prices)

#         # Group options by strike
#         grouped = defaultdict(lambda: {"call": None, "put": None})
#         for option in option_qs:
#             key = Decimal(option.strike)
#             if option.option_type == "call":
#                 grouped[key]["call"] = option
#             elif option.option_type == "put":
#                 grouped[key]["put"] = option

#         updated_count = 0
#         for strike, pair in grouped.items():
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

#                 p_over, p_under = calculate_implied_probability_risk_neutral(
#                     call_bid=call_bid,
#                     call_ask=call_ask,
#                     put_bid=put_bid,
#                     put_ask=put_ask
#                 )

#                 over_american = get_american_odds_from_ladder(
#                     p_over, ODDS_LADDER_JSON, side="home", vig_percent=vig_percent)
#                 under_american = get_american_odds_from_ladder(
#                     p_under, ODDS_LADDER_JSON, side="away", vig_percent=vig_percent)

#                 # Update Over market
#                 Market.objects.update_or_create(
#                     stock=stock,
#                     target_price=strike,
#                     expiry_date=expiration,
#                     outcome_type="over",
#                     defaults={
#                         "implied_odds_over": p_over,
#                         "implied_odds_under": p_under,
#                         "display_odds_over": over_american,
#                         "display_odds_under": under_american,
#                         "is_active": True
#                     }
#                 )

#                 # Update Under market
#                 Market.objects.update_or_create(
#                     stock=stock,
#                     target_price=strike,
#                     expiry_date=expiration,
#                     outcome_type="under",
#                     defaults={
#                         "implied_odds_over": p_over,
#                         "implied_odds_under": p_under,
#                         "display_odds_over": under_american,
#                         "display_odds_under": over_american,
#                         "is_active": True
#                     }
#                 )

#                 updated_count += 2

#             except Exception as e:
#                 print(f"Error processing strike {strike}: {e}")
#                 continue

#         return Response({
#             "message": f"{updated_count} markets updated with vig {vig_percent}% for {symbol} {expiration}."
#         }, status=200)



# NEW: MarketVigAdjustmentAPIView
class MarketVigAdjustmentAPIView(APIView):
    """
    API View for an admin to adjust the vig applied to a specific market's odds display.
    Requires 'market_id' and 'new_vig_percentage'.
    """

    authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAdminUser] # Only admin users can adjust vig

    def post(self, request, *args, **kwargs):
        serializer = MarketVigAdjustmentSerializer(data=request.data)
        serializer.is_valid(
            raise_exception=True
        )  # Validate input, raise 400 if invalid

        market_id = serializer.validated_data["market_id"]
        new_vig_percentage = serializer.validated_data["new_vig_percentage"]

        try:
            market = Market.objects.get(id=market_id)

            if not market.is_active:
                return Response(
                    {
                        "error": f"Market {market_id} is not active. Vig can only be adjusted for active markets."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Use the implied (true) probabilities as the base for recalculating vig
            implied_over = market.implied_odds_over
            implied_under = market.implied_odds_under

            if implied_over is None or implied_under is None:
                return Response(
                    {
                        "error": f"Market {market_id} does not have implied odds set. Run update_market_odds first."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --- Recalculate display odds with the new vig ---
            with transaction.atomic():
                # Apply the new vig to the *true* implied probabilities
                # Note: apply_vig utility needs total_prob_sum
                total_implied_prob_sum = (
                    implied_over + implied_under
                )  # Should be approx 1.0

                display_prob_over = apply_vig(
                    implied_over,
                    total_implied_prob_sum,
                    vig_percentage=new_vig_percentage,
                )
                display_prob_under = apply_vig(
                    implied_under,
                    total_implied_prob_sum,
                    vig_percentage=new_vig_percentage,
                )

                # Convert these new probabilities to American odds
                new_display_odds_over = convert_decimal_to_american_odds(
                    display_prob_over
                )
                new_display_odds_under = convert_decimal_to_american_odds(
                    display_prob_under
                )

                if new_display_odds_over is None or new_display_odds_under is None:
                    return Response(
                        {
                            "error": f"Failed to convert new vig-adjusted probabilities to American odds for market {market_id}. Check vig percentage or market probabilities."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Update the market instance
                market.display_odds_over = new_display_odds_over
                market.display_odds_under = new_display_odds_under
                market.updated_at = timezone.now()
                market.save()

                logger.info(
                    f"Vig adjusted for Market {market_id} to {new_vig_percentage:.2%}. New odds: Over={new_display_odds_over}, Under={new_display_odds_under}"
                )

                # Return the updated market data
                serializer = MarketSerializer(
                    market
                )  # Reuse MarketSerializer for output
                return Response(
                    {
                        "message": f"Vig successfully adjusted for market {market_id}.",
                        "market": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

        except Market.DoesNotExist:
            return Response(
                {"error": "Market not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(
                f"Error adjusting vig for market {market_id}: {e}", exc_info=True
            )
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
