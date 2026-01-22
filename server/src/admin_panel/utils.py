# bets/utils.py
from datetime import datetime
from betengine.models import Stock, Bet, Market
from datetime import timedelta, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import defaultdict
from django.core.cache import cache
from django.db.models.functions import Coalesce
from django.db.models import Sum, F, OuterRef, Subquery, Value, DecimalField, Count
from betengine.utils import american_to_decimal_odds, american_to_fractional_odds
from user.models import KYCProfile, Profile
from rest_framework import status
def round_two_places(value):
    """Safely round any numeric-like value to two decimal places."""
    try:
        if value is None or value == "" or value == "-":
            return None
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError):
        return None
def get_bet_volume(stock_symbol, strike, expiration):
    if isinstance(expiration, str):
        try:
            expiration = datetime.strptime(expiration, "%Y-%m-%d").date()
        except ValueError:
            return 0  # Invalid date

    try:
        stock_obj = Stock.objects.get(symbol=stock_symbol)
    except Stock.DoesNotExist:
        return 0  # No matching stock

    return (
        Bet.objects.filter(
            market__stock=stock_obj,
            market__target_price=strike,
            market__expiry_date=expiration
        ).aggregate(total=Sum('amount_wagered'))['total'] or 0
    )


# ----------------------------
# Already defined ones earlier
# ----------------------------
def get_daily_volume(start_date=None):
    qs = Bet.objects.all()
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    return qs.aggregate(total=Sum("amount_wagered"))["total"] or 0

def get_active_users_last_30_days():
    thirty_days_ago = date.today() - timedelta(days=30)
    return Bet.objects.filter(created_at__date__gte=thirty_days_ago).values(
        "user"
    ).distinct().count()

def get_total_profits(month_to_date=False):
    bets = Bet.objects.all()
    if month_to_date:
        start_of_month = date.today().replace(day=1)
        bets = bets.filter(created_at__date__gte=start_of_month)

    total_wagered = bets.aggregate(
        total=Coalesce(Sum("amount_wagered"), Decimal("0.00"))
    )["total"]
    total_payouts = bets.aggregate(
        total=Coalesce(Sum("payout_amount"), Decimal("0.00"))
    )["total"]

    return total_wagered - total_payouts

def get_liabilities_snapshot(limit=5):
    return (
        Market.objects.annotate(
            total_liability=Coalesce(Sum("bets__amount_wagered"), Decimal("0.00"))
        )
        .values(
            ticker=F("stock__symbol"),
            expiry=F("expiry_date"),
            strike=F("target_price"),
            total_liability=F("total_liability"),
        )
        .order_by("-total_liability")[:limit]
    )


def get_pending_kyc_count():
    return KYCProfile.objects.filter(kyc_status="pending").count()

def get_pending_bet_settlement_count():
    return Bet.objects.filter(status="pending").count()

# 7. Profits vs. losses (last 6 months)
# Profit = won bets payout - stake, Loss = stake of lost bets
def get_profits_vs_losses_last_6_months():
    six_months_ago = date.today() - timedelta(days=180)
    bets = Bet.objects.filter(created_at__date__gte=six_months_ago)

    monthly_data = []
    for i in range(6):
        start_date = (date.today().replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1)

        month_bets = bets.filter(created_at__date__gte=start_date, created_at__date__lt=end_date)

        total_profits = month_bets.filter(status="won").aggregate(
            total=Coalesce(Sum("payout_amount") - Sum("amount_wagered"), Decimal("0.00"))
        )["total"]

        total_losses = month_bets.filter(status="lost").aggregate(
            total=Coalesce(Sum("amount_wagered"), Decimal("0.00"))
        )["total"]

        monthly_data.append({
            "month": start_date.strftime("%b"),
            "profits": total_profits,
            "losses": total_losses
        })

    return list(reversed(monthly_data))  # so oldest first

# 8. Win/Loss ratio (last 6 months)
def get_win_loss_ratio_last_6_months():
    six_months_ago = date.today() - timedelta(days=180)
    bets = Bet.objects.filter(created_at__date__gte=six_months_ago)

    wins = bets.filter(status="won").count()
    losses = bets.filter(status="lost").count()

    return {
        "wins": wins,
        "losses": losses
    }

# 9. Recent bets (last 5)
def get_recent_bets(limit=5):
    return Bet.objects.select_related("user", "market").order_by("-created_at")[:limit]

# 10. Settlement ratio (last 6 months)
def get_settlement_ratio_last_6_months():
    six_months_ago = date.today() - timedelta(days=180)
    bets = Bet.objects.filter(created_at__date__gte=six_months_ago)

    settled = bets.exclude(status="pending").count()
    pending = bets.filter(status="pending").count()

    return {
        "settled": settled,
        "pending": pending
    }

def get_user_bet_stats(user=None):
    """
    Highly optimized version of user bet statistics aggregation.
    Efficient for hundreds or thousands of users.
    """

    from betengine.models import Bet

    # --- Subqueries for Bet Aggregations ---
    total_wager_subquery = (
        Bet.objects.filter(user=OuterRef("user"))
        .values("user")
        .annotate(total=Coalesce(Sum("amount_wagered"), Value(0, output_field=DecimalField())))
        .values("total")[:1]
    )

    total_payout_subquery = (
        Bet.objects.filter(user=OuterRef("user"))
        .values("user")
        .annotate(total=Coalesce(Sum("payout_amount"), Value(0, output_field=DecimalField())))
        .values("total")[:1]
    )

    bet_count_subquery = (
        Bet.objects.filter(user=OuterRef("user"))
        .values("user")
        .annotate(count=Coalesce(Count("id"), Value(0)))  # ✅ works now
        .values("count")[:1]
    )
    # --- Base QuerySet ---
    qs = (
        Profile.objects.select_related("user")
        .prefetch_related("user__wallet", "user__kyc_profile")
        .annotate(
            total_wager=Coalesce(Subquery(total_wager_subquery), Value(0, output_field=DecimalField())),
            total_payout=Coalesce(Subquery(total_payout_subquery), Value(0, output_field=DecimalField())),
            bet_count=Coalesce(Subquery(bet_count_subquery), Value(0)),
        )
    )

    if user:
        qs = qs.filter(user=user)

    data = []
    for profile in qs:
        user_obj = profile.user

        # --- Wallet ---
        balance = Decimal("0.00")
        if hasattr(user_obj, "wallet") and user_obj.wallet:
            balance = user_obj.wallet.balance

        # --- KYC ---
        kyc_status = "pending"
        if hasattr(user_obj, "kyc_profile") and user_obj.kyc_profile:
            kyc_status = user_obj.kyc_profile.kyc_status or "pending"

        # --- GGR ---
        ggr_value = profile.total_wager - profile.total_payout

        data.append({
            "username": user_obj.username,
            "email": user_obj.email,
            "balance": round(balance, 2),
            "crs": profile.crs_risk_score if profile.crs_risk_score > 0 else 1.0,
            "crs_level": profile.crs_risk_level,
            "max_wager_allowed": profile.max_stake,
            "ggr": round(ggr_value, 2),
            "bet_count": profile.bet_count,
            "kyc_status": kyc_status,
        })

    return data


CACHE_TIMEOUT = 60 * 5  # 5 minutes cache


def get_grouped_market_data(symbol: str):
    """
    Returns grouped market data for a given stock symbol.
    Fully aligned with Market + odds ladder structure.
    Used by both GroupedMarketView and MarketOddsNudgeView.
    """

    cache_key = f"market_grouped_{symbol}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # --- Fetch Stock ---
    try:
        stock = Stock.objects.only(
            "id", "symbol", "company_name", "url",
            "last_price", "last_change", "last_percent_change"
        ).get(symbol=symbol)
    except Stock.DoesNotExist:
        return {
            "detail": f"Stock '{symbol}' not found",
            "status": status.HTTP_404_NOT_FOUND,
        }

    # --- Fetch Markets ---
    markets = Market.objects.filter(stock=stock).only(
        "id",
        "expiry_date",
        "target_price",
        "display_odds_over",
        "display_odds_under",
        "implied_odds_over",
        "implied_odds_under",
        "is_active",
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

    cache.set(cache_key, response_data, CACHE_TIMEOUT)
    return response_data


def get_total_ggr(start_date=None, end_date=None, active_users_only=False):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    """
    Returns GGR stats for all users, optionally filtered by date range and active bets.
    """
    bets = Bet.objects.all()

    if start_date:
        bets = bets.filter(created_at__date__gte=start_date)
    if end_date:
        bets = bets.filter(created_at__date__lte=end_date)

    if active_users_only:
        active_user_ids = Bet.objects.filter(status="pending") \
                                    .values_list("user_id", flat=True).distinct()
        users_count = User.objects.filter(id__in=active_user_ids).count()
    else:
        users_count = User.objects.count()

    total_wager = bets.aggregate(total=Sum("amount_wagered"))["total"] or 0
    total_payout = bets.aggregate(total=Sum("payout_amount"))["total"] or 0
    ggr = round(total_wager - total_payout, 2)

    return {
        "ggr": ggr,
        "total_wager": round(total_wager, 2),
        "total_payout": round(total_payout, 2),
        "users": users_count
    }