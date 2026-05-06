# populate.py
import time
import logging
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
from django.db import transaction
from django.db.models import Sum
from django.conf import settings
from django_q.tasks import async_task
from django.utils import timezone
from django.core.cache import cache

from .market_chart import ODDS_LADDER_JSON
from .utils import calculate_implied_probability_risk_neutral, get_side_and_american_odds
from .models import OptionData
from betengine.models import Market, Bet, Stock

logger = logging.getLogger(__name__)


def update_market_odds_from_feed(market, feed_data):
    """
    Applies fresh Alpha Vantage implied probabilities,
    while keeping stored manual nudges persistent.
    """
    try:
        base_over = Decimal(feed_data["implied_prob_over"])
        base_under = Decimal(feed_data["implied_prob_under"])
    except Exception as e:
        logger.warning("[%s] Invalid feed data for market %s: %s", market.stock.symbol, market.id, e)
        return

    # --- Step 1: Reset to fresh feed baseline ---
    market.feed_implied_odds_over = base_over
    market.feed_implied_odds_under = base_under
    market.implied_odds_over = base_over
    market.implied_odds_under = base_under
    market.save(update_fields=[
        "feed_implied_odds_over", "feed_implied_odds_under",
        "implied_odds_over", "implied_odds_under", "updated_at"
    ])

    # --- Step 2: Reapply stored nudges ---
    if market.nudge_offset_over or market.nudge_offset_under:
        logger.info(
            "[%s] Reapplying nudges for market #%s (over=%s, under=%s)",
            market.stock.symbol,
            market.id,
            market.nudge_offset_over,
            market.nudge_offset_under,
        )
        for _ in range(abs(market.nudge_offset_over)):
            direction = 1 if market.nudge_offset_over > 0 else -1
            market.apply_nudge(side="over", direction=direction)
        for _ in range(abs(market.nudge_offset_under)):
            direction = 1 if market.nudge_offset_under > 0 else -1
            market.apply_nudge(side="under", direction=direction)
    # else:
    #     # No stored nudges — just set feed odds
    #     market.implied_odds_over = base_over
    #     market.implied_odds_under = base_under
    #     market.save(update_fields=["implied_odds_over", "implied_odds_under", "updated_at"])
    # --- Step 3: Invalidate cache for live UI refresh ---
    cache.delete(f"market_grouped_{market.stock.symbol}")


# ✅ Main population task
def populate_market_for_stocks(
    stock_ids,
    job_start: float = None,
    job_budget: int = 240,
    refresh_prices: bool = True,
):
    """
    Populate/refresh Market objects for a list of stock IDs.
    Integrates Alpha Vantage feed data and reapplies stored manual nudges.
    """
    if not stock_ids:
        return

    if not job_start:
        job_start = time.time()
    deadline = job_start + job_budget

    remaining = []
    for stock_id in stock_ids:
        if time.time() > (deadline - 8):
            logger.warning("⏰ Time budget reached — deferring remaining stocks.")
            remaining = stock_ids[stock_ids.index(stock_id):]
            break

        try:
            stock = Stock.objects.get(id=stock_id)
        except Stock.DoesNotExist:
            logger.error("❌ Stock id=%s does not exist — skipping", stock_id)
            continue

        markets_created = 0
        valid_market_keys = set()

        try:
            # Step 1: Resolve the current stock price.
            if refresh_prices:
                try:
                    current_price = stock.get_current_price(
                        api_key=getattr(settings, "ALPHA_VANTAGE_API_KEY", None)
                    )
                except Exception as e:
                    logger.exception("[%s] Price fetch failed: %s", stock.symbol, e)
                    current_price = stock.last_price
            else:
                current_price = stock.last_price

            if not current_price or current_price <= 0:
                logger.warning("[%s] Invalid price: %s", stock.symbol, current_price)
                continue

            lower_bound = current_price * Decimal("0.85")
            upper_bound = current_price * Decimal("1.15")
            today = timezone.now().date()

            # Step 2: Gather option data
            latest_quote_date = (
                OptionData.objects.filter(symbol__iexact=stock.symbol, expiration__gte=today)
                .order_by("-quote_date")
                .values_list("quote_date", flat=True)
                .first()
            )
            option_qs = OptionData.objects.filter(
                symbol__iexact=stock.symbol,
                expiration__gte=today,
            )
            if latest_quote_date:
                option_qs = option_qs.filter(quote_date=latest_quote_date)
            if not option_qs.exists():
                logger.info("[%s] No options found.", stock.symbol)
                Market.objects.filter(
                    stock=stock,
                    outcome_type="over",
                    expiry_date__gte=today,
                    is_active=True,
                ).update(is_active=False)
                cache.delete(f"market_grouped_{stock.symbol}")
                continue

            grouped = defaultdict(lambda: {"call": None, "put": None})
            for option in option_qs:
                try:
                    key = (option.symbol, option.expiration, Decimal(option.strike))
                    grouped[key][option.option_type] = option
                except Exception as e:
                    logger.warning("[%s] Skipping invalid option %s: %s", stock.symbol, getattr(option, "contract_id", "N/A"), e)
                    continue

            # Step 3: Calculate implied probabilities and update markets
            for (symbol, expiration_date, strike), pair in grouped.items():
                call, put = pair.get("call"), pair.get("put")
                if not (call and put):
                    continue

                try:
                    call_mark = Decimal(call.mark or 0)
                    put_mark = Decimal(put.mark or 0)
                except Exception:
                    continue

                if call_mark <= 0 or put_mark <= 0:
                    continue
                if not (lower_bound <= strike <= upper_bound):
                    continue

                p_over, p_under = calculate_implied_probability_risk_neutral(call_mark=call_mark, put_mark=put_mark)
                if not Market.probabilities_within_guardrail(p_over, p_under):
                    continue

                first_side, first_american_odd = get_side_and_american_odds(p_over, ODDS_LADDER_JSON, vig=Decimal("9.0"))
                second_side, second_american_odd = get_side_and_american_odds(p_under, ODDS_LADDER_JSON, vig=Decimal("9.0"))

                display_odds = {"over": first_american_odd, "under": second_american_odd}
                ladder_favored_side = first_side.lower() if first_american_odd <= second_american_odd else second_side.lower()

                option_volume_total = int(call.volume or 0) + int(put.volume or 0)
                bet_volume = (
                    Bet.objects.filter(
                        market__stock=stock,
                        market__target_price=strike,
                        market__expiry_date=expiration_date,
                    ).aggregate(total=Sum("amount_wagered"))["total"] or 0
                )
                total_volume = option_volume_total + (2 * int(bet_volume))
                if total_volume == 0:
                    continue

                valid_market_keys.add((strike, expiration_date))

                # Step 4: Create or update Market
                with transaction.atomic():
                    market, _ = Market.objects.update_or_create(
                        stock=stock,
                        target_price=strike,
                        expiry_date=expiration_date,
                        outcome_type="over",
                        defaults={
                            "feed_implied_odds_over": p_over,
                            "feed_implied_odds_under": p_under,
                            "implied_odds_over": p_over,
                            "implied_odds_under": p_under,
                            "display_odds_over": display_odds["over"],
                            "display_odds_under": display_odds["under"],
                            "ladder_favored_side": ladder_favored_side,
                            "total_volume": total_volume,
                            "is_active": True,
                        },
                    )

                    # ✅ Reapply nudges on top of fresh data
                    # update_market_odds_from_feed(
                    #     market,
                    #     {"implied_prob_over": p_over, "implied_prob_under": p_under},
                    # )

                    markets_created += 1

            active_markets = list(
                Market.objects.filter(
                    stock=stock,
                    outcome_type="over",
                    expiry_date__gte=today,
                    is_active=True,
                ).values_list("id", "target_price", "expiry_date")
            )
            stale_market_ids = [
                market_id
                for market_id, target_price, expiry_date in active_markets
                if (target_price, expiry_date) not in valid_market_keys
            ]

            if stale_market_ids:
                Market.objects.filter(id__in=stale_market_ids).update(is_active=False)

            cache.delete(f"market_grouped_{stock.symbol}")
            logger.info("[%s] %d markets created/updated", stock.symbol, markets_created)

        except Exception as e:
            logger.exception("[%s] Unexpected failure: %s", stock.symbol, e)
            continue

    # If budget exceeded, re-enqueue
    if remaining:
        try:
            logger.info("Re-enqueueing %d remaining stocks.", len(remaining))
            # Re-enqueue the guarded population path, not the legacy tasks.py helper.
            async_task("mkt.populate.populate_market_for_stocks", remaining, task_name="populate_market_resume")
        except Exception:
            logger.exception("Failed to re-enqueue remaining stocks.")

    logger.info("✅ Market population finished for provided stocks.")
