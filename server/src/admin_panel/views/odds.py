# admin_panel/views/odds.py
from decimal import Decimal

from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

# from betengine.models import Odds


class MarketOddsNudgeView(APIView):
    """
    Nudges a market's odds up or down the odds ladder.
    Returns the full grouped market response (like GroupedMarketView),
    so the frontend sees the updated odds immediately.
    """

    @transaction.atomic
    def post(self, request, market_id):
        try:
            market = Market.objects.select_related("stock").get(id=market_id)
        except Market.DoesNotExist:
            return Response(
                {"detail": f"Market with id {market_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # --- Validate input ---
        side = request.data.get("side")
        direction = request.data.get("direction")

        if side not in ["over", "under"]:
            return Response({"detail": "side must be 'over' or 'under'"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            direction = int(direction)
        except (TypeError, ValueError):
            return Response({"detail": "direction must be an integer (+1 or -1)"},
                            status=status.HTTP_400_BAD_REQUEST)

        if direction not in [-1, 1]:
            return Response({"detail": "direction must be +1 (up) or -1 (down)"},
                            status=status.HTTP_400_BAD_REQUEST)

        # --- Determine which side to nudge ---
        current_br_true_percent = (
            market.br_true_percent_over if side == "over" else market.br_true_percent_under
        )

        # --- Call utility function ---
        new_odds = nudge_odds_ladder(
            current_br_true_percent=current_br_true_percent,
            nudge_direction=direction,
            odds_ladder=ODDS_LADDER_JSON,
            vig_key="vig_9_0_percent",
        )

        if not new_odds:
            return Response({"detail": "Unable to nudge odds (edge of ladder reached)."},
                            status=status.HTTP_400_BAD_REQUEST)

        # --- Apply new odds to Market ---
        if side == "over":
            market.br_true_percent_over = new_odds["br_true_percent"]
            market.implied_odds_over = Decimal(new_odds["br_true_percent"]) / 100
            market.display_odds_over = new_odds["american_odds"]

            market.br_true_percent_under = new_odds["br_true_percent_opposite"]
            market.implied_odds_under = Decimal(new_odds["br_true_percent_opposite"]) / 100
        else:
            market.br_true_percent_under = new_odds["br_true_percent"]
            market.implied_odds_under = Decimal(new_odds["br_true_percent"]) / 100
            market.display_odds_under = new_odds["american_odds"]

            market.br_true_percent_over = new_odds["br_true_percent_opposite"]
            market.implied_odds_over = Decimal(new_odds["br_true_percent_opposite"]) / 100

        market.save()

        # --- Invalidate cached grouped markets ---
        cache.delete(f"market_grouped_{market.stock.symbol}")

        # --- Return the full grouped market payload ---
        grouped_view = GroupedMarketView()
        request._request.GET = request._request.GET.copy()
        request._request.GET["symbol"] = market.stock.symbol
        response = grouped_view.get(request._request)

        return response



# class UpdateOddsView(APIView):
#     permission_classes = [IsAdminUser]

#     def post(self, request):
#         symbol = request.data.get("symbol")
#         over_odds = request.data.get("over_odds")
#         under_odds = request.data.get("under_odds")
#         target_price = request.data.get("target_price")

#         if not symbol or not over_odds or not under_odds or not target_price:
#             return Response(
#                 {
#                     "error": "All fields (symbol, over_odds, under_odds, target_price) are required."
#                 },
#                 status=400,
#             )

#         try:
#             odds_obj, _ = Odds.objects.update_or_create(
#                 symbol=symbol.upper(),
#                 defaults={
#                     "over_odds": Decimal(over_odds),
#                     "under_odds": Decimal(under_odds),
#                     "target_price": Decimal(target_price),
#                 },
#             )
#             return Response(
#                 {"message": f"Odds for {symbol.upper()} updated successfully."}
#             )
#         except Exception as e:
#             return Response({"error": str(e)}, status=500)


# class OddsOverrideView(APIView):
#     def post(self, request):
#         # Apply override
#         return Response({"message": "Odds updated"})
