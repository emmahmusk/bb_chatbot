"""
app/analytics/utils.py

Analytics helpers for Bets, Parlays, Markets and Stocks.

Assumptions:
- Models are available in `betengine.models` or `your_app.models` (adjust imports below).
- User profile is available via `user.profile` (Profile model provided).
- Decimal monetary fields: Bet.amount_wagered, Bet.payout_amount, ParlayBet.amount_wagered, ParlayBet.payout_amount.
- Market <-> Stock relation: Market.stock (FK to Stock).

All monetary values returned as strings (e.g. "123.45") to avoid JSON float rounding problems.
"""

from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from datetime import datetime, timedelta, date

from django.db.models import (
    Sum, Count, F, Q, Value, Case, When, DecimalField, ExpressionWrapper, Prefetch
)
from django.db.models.functions import Coalesce, Concat
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth import get_user_model
# Replace 'betengine' with your real app name if different
from betengine.models import Bet, ParlayBet, Market, Stock
from collections import defaultdict
from user.models import Profile, Wallet  # adjust import path if your Profile lives elsewhere
User = get_user_model()
# increase decimal precision for intermediary calculations
getcontext().prec = 12

# ---------- Constants (tuneable) ----------
DEFAULT_EXPOSURE_LIMIT_CRS_1 = Decimal("500.00")  # baseline amount a CRS=1.0 user can win
MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE = 25

def round_two_places(value):
    """Safely round any numeric-like value to two decimal places."""
    try:
        if value is None or value == "" or value == "-":
            return None
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except Exception:
        return None

# ---------- Small helpers ----------
def _to_decimal(value: Optional[Any]) -> Decimal:
    """Convert numeric-ish value to Decimal safely."""
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def money_str(value: Optional[Any]) -> str:
    """Return value as quantized string with 2 decimals."""
    dec = _to_decimal(value)
    return str(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def safe_div(numer: Decimal, denom: Decimal, precision: int = 4) -> Decimal:
    """Safe division returning Decimal('0') on zero denominator."""
    try:
        if not denom:
            return Decimal("0")
        return (numer / denom).quantize(Decimal(f"0.{'0'*(precision-1)}1"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0")


def parse_date_range(date_from: Optional[str], date_to: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse YYYY-MM-DD or ISO date strings. Returns naive datetimes in timezone-aware form (UTC).
    If only one bound provided, normalize the other to start/end of that day.
    """
    def _parse(d):
        if not d:
            return None
        try:
            # Try ISO first (handles YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS)
            dt = datetime.fromisoformat(d)
            if dt.tzinfo is None:
                # make timezone-aware using Django timezone
                return timezone.make_aware(dt)
            return dt
        except Exception:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
                return timezone.make_aware(dt)
            except Exception:
                return None

    dt_from = _parse(date_from)
    dt_to = _parse(date_to)

    if dt_from and not dt_to:
        dt_to = dt_from + timedelta(days=1) - timedelta(seconds=1)
    if dt_to and not dt_from:
        dt_from = dt_to.replace(hour=0, minute=0, second=0)

    return dt_from, dt_to


# ---------- Odds helpers ----------
def american_to_decimal(american: Optional[str]) -> Decimal:
    """
    Convert American odds string to Decimal odds.
    Accepts strings like "-110", "+150", "150" or decimal numeric strings.
    Returns Decimal rounded to 2dp.
    """
    if american is None:
        return Decimal("0")
    try:
        a = Decimal(str(american).strip())
    except Exception:
        return Decimal("0")
    if a == 0:
        return Decimal("0")
    if a > 0:
        dec = (a / Decimal("100")) + Decimal("1")
    else:
        dec = (Decimal("100") / abs(a)) + Decimal("1")
    return dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def potential_win_for_stake(american_odds: Optional[str], stake: Decimal) -> Decimal:
    """
    Return how much the user would win (not including stake) for given stake and American odds.
    Example: odds +100, stake 100 => win 100
             odds -110, stake 110 => win 100
    """
    dec = american_to_decimal(american_odds)
    if dec <= 0:
        return Decimal("0")
    # payout - stake = stake * (dec - 1)
    profit = (stake * (dec - Decimal("1"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return profit


def stake_limit_for_max_win(american_odds: Optional[str], max_allowed_win: Decimal) -> Decimal:
    """
    Given american odds (string) and maximum allowed win (max_allowed_win),
    compute the maximum stake that would yield at most max_allowed_win profit.
    If potential win per unit stake is zero => returns 0.
    """
    dec = american_to_decimal(american_odds)
    if dec <= Decimal("1.00"):
        return Decimal("0.00")
    per_unit_win = (dec - Decimal("1.00"))
    try:
        stake = (max_allowed_win / per_unit_win).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        stake = Decimal("0.00")
    return stake


# ---------- CRS / Exposure helpers ----------
def profile_crs_decimal(profile: Optional[Profile]) -> Decimal:
    """
    Return CRS as a Decimal multiplier.
    - If profile.crs_risk_score stores 1 meaning baseline -> return Decimal('1').
    - If missing -> default to Decimal('1').
    """
    if profile is None:
        return Decimal("1.0")
    try:
        score = profile.crs_risk_score or 1
        # interpret integer score as multiplier (so 1 => 1.0)
        return Decimal(str(score)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("1.0")


def exposure_limit_for_profile(profile: Optional[Profile], base_limit: Decimal = DEFAULT_EXPOSURE_LIMIT_CRS_1) -> Decimal:
    """
    Calculate exposure (max allowed win) for a user based on their CRS.
    Default: CRS 1 -> base_limit. CRS multiplier scales linearly.
    """
    mult = profile_crs_decimal(profile)
    return (base_limit * mult).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------- Aggregation functions ----------

def get_top_users_by_ggr(start_date=None, end_date=None, top_n=5, reverse=False, include_parlays=False):
    """
    Returns top or worst users based on combined GGR from both Bet and ParlayBet.
    """
    bets = Bet.objects.select_related("user").all()
    if start_date:
        bets = bets.filter(created_at__date__gte=start_date)
    if end_date:
        bets = bets.filter(created_at__date__lte=end_date)

    bet_data = (
        bets.values("user__id", "user__username")
        .annotate(
            total_wager=Coalesce(Sum("amount_wagered"), Value(0, output_field=DecimalField())),
            total_payout=Coalesce(Sum("payout_amount"), Value(0, output_field=DecimalField())),
        )
        .annotate(ggr=F("total_wager") - F("total_payout"))
    )

    # ---- Merge Parlay Bets if required ----
    if include_parlays:
        parlays = ParlayBet.objects.select_related("user")
        if start_date:
            parlays = parlays.filter(created_at__date__gte=start_date)
        if end_date:
            parlays = parlays.filter(created_at__date__lte=end_date)

        parlay_data = (
            parlays.values("user__id", "user__username")
            .annotate(
                total_wager=Coalesce(Sum("amount_wagered"), Value(0, output_field=DecimalField())),
                total_payout=Coalesce(Sum("payout_amount"), Value(0, output_field=DecimalField())),
            )
            .annotate(ggr=F("total_wager") - F("total_payout"))
        )

        # Merge both datasets by user
        combined = defaultdict(lambda: {"user_id": None, "username": "", "ggr": Decimal("0.00")})
        for dataset in [bet_data, parlay_data]:
            for u in dataset:
                uid = u["user__id"]
                combined[uid]["user_id"] = uid
                combined[uid]["username"] = u["user__username"]
                combined[uid]["ggr"] += u["ggr"]

        combined_values = list(combined.values())
        combined_values.sort(key=lambda x: x["ggr"], reverse=not reverse)
        return [
            {
                "user_id": u["user_id"],
                "username": u["username"],
                "ggr": round_two_places(u["ggr"]),
            }
            for u in combined_values[:top_n]
        ]

    # Fallback (single bets only)
    ordered = bet_data.order_by("-ggr" if not reverse else "ggr")[:top_n]
    return [
        {"user_id": u["user__id"], "username": u["user__username"], "ggr": round_two_places(u["ggr"])}
        for u in ordered
    ]

def get_active_inactive_users():
    """Return count of active (30d bettors) and inactive users."""
    thirty_days_ago = date.today() - timedelta(days=30)
    active_ids = (
        Bet.objects.filter(created_at__date__gte=thirty_days_ago)
        .values_list("user_id", flat=True)
        .distinct()
    )
    active_count = len(active_ids)
    total_users = Profile.objects.count()
    return active_count, total_users - active_count
def overall_analytics(date_from=None, date_to=None):
    """
    Returns high-level overview metrics: total wagers, payouts, GGR, CRS, and user stats.
    Includes both single bets and parlay bets.
    """
    today = timezone.now().date()

    # ---- Single Bets ----
    bets = Bet.objects.select_related("user")
    if date_from:
        bets = bets.filter(created_at__date__gte=date_from)
    if date_to:
        bets = bets.filter(created_at__date__lte=date_to)

    bet_wager = bets.aggregate(total=Coalesce(Sum("amount_wagered"), Decimal("0.00")))["total"]
    bet_payout = bets.aggregate(total=Coalesce(Sum("payout_amount"), Decimal("0.00")))["total"]

    # ---- Parlay Bets ----
    parlay_qs = ParlayBet.objects.select_related("user")
    if date_from:
        parlay_qs = parlay_qs.filter(created_at__date__gte=date_from)
    if date_to:
        parlay_qs = parlay_qs.filter(created_at__date__lte=date_to)

    parlay_wager = parlay_qs.aggregate(total=Coalesce(Sum("amount_wagered"), Decimal("0.00")))["total"]
    parlay_payout = parlay_qs.aggregate(total=Coalesce(Sum("payout_amount"), Decimal("0.00")))["total"]

    # ---- Combine both ----
    total_wager = bet_wager + parlay_wager
    total_payout = bet_payout + parlay_payout
    ggr = total_wager - total_payout

    # ---- User activity ----
    active_users, inactive_users = get_active_inactive_users()

    # ---- Top / Worst Users (including parlay GGR) ----
    top_users = get_top_users_by_ggr(date_from, date_to, top_n=5, include_parlays=True)
    worst_users = get_top_users_by_ggr(date_from, date_to, top_n=5, reverse=True, include_parlays=True)

    if total_wager:
        hold_pct = (ggr / total_wager * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "date_range": {"from": date_from, "to": date_to or today},
        "total_wager": round_two_places(total_wager),
        "total_payout": round_two_places(total_payout),
        "ggr": round_two_places(ggr),
        "hold_percent": str(hold_pct),
        "active_users": active_users,
        "inactive_users": inactive_users,
        "top_users": top_users,
        "worst_users": worst_users,
        "last_updated": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

# def overall_analytics(date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
#     """
#     Compute overall aggregates across Bet and ParlayBet.
#     Returns:
#       - total_bet_count (single bets),
#       - total_parlay_count,
#       - total_handle (sum of all amounts wagered incl parlays),
#       - total_payout (sum of payouts),
#       - ggr (handle - payout),
#       - hold_percent (ggr / handle * 100)
#     """
#     dt_from, dt_to = parse_date_range(date_from, date_to)

#     bet_qs = Bet.objects.all()
#     parlay_qs = ParlayBet.objects.all()

#     if dt_from:
#         bet_qs = bet_qs.filter(created_at__gte=dt_from)
#         parlay_qs = parlay_qs.filter(created_at__gte=dt_from)
#     if dt_to:
#         bet_qs = bet_qs.filter(created_at__lte=dt_to)
#         parlay_qs = parlay_qs.filter(created_at__lte=dt_to)

#     # Aggregate singles
#     bet_agg = bet_qs.aggregate(
#         count=Coalesce(Count('id'), 0),
#         handle=Coalesce(Sum('amount_wagered'), Decimal("0.00")),
#         payout=Coalesce(Sum('payout_amount'), Decimal("0.00")),
#     )
#     # Aggregate parlays
#     parlay_agg = parlay_qs.aggregate(
#         count=Coalesce(Count('id'), 0),
#         handle=Coalesce(Sum('amount_wagered'), Decimal("0.00")),
#         payout=Coalesce(Sum('payout_amount'), Decimal("0.00")),
#     )

#     # Combine
#     total_bet_count = int(bet_agg['count'] or 0)
#     total_parlay_count = int(parlay_agg['count'] or 0)
#     total_handle = _to_decimal(bet_agg['handle']) + _to_decimal(parlay_agg['handle'])
#     total_payout = _to_decimal(bet_agg['payout']) + _to_decimal(parlay_agg['payout'])
#     ggr = (total_handle - total_payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

#     hold_pct = Decimal("0.00")
#     if total_handle:
#         hold_pct = (ggr / total_handle * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

#     return {
#         "total_single_bets": total_bet_count,
#         "total_parlay_bets": total_parlay_count,
#         "total_handle": money_str(total_handle),
#         "total_payout": money_str(total_payout),
#         "ggr": money_str(ggr),
#         "hold_percent": str(hold_pct),
#         "date_from": dt_from.isoformat() if dt_from else None,
#         "date_to": dt_to.isoformat() if dt_to else None,
#     }


def stock_summary(date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return per-stock aggregated metrics.
    For each Stock:
      - symbol, company_name
      - total_bets_count (singles), total_parlay_count (parlays),
      - handle, payout, ggr, hold_percent
      - active_markets_count, total_volume (market.total_volume sum)
    The aggregation uses Bet.market__stock relationship and ParlayLegs (legs -> parlay_bet).
    """
    dt_from, dt_to = parse_date_range(date_from, date_to)

    # Aggregate single bets by stock
    bet_qs = Bet.objects.filter(market__isnull=False).select_related('market__stock')
    if dt_from:
        bet_qs = bet_qs.filter(created_at__gte=dt_from)
    if dt_to:
        bet_qs = bet_qs.filter(created_at__lte=dt_to)

    bet_by_stock = (
        bet_qs.values(stock_symbol=F('market__stock__symbol'), stock_name=F('market__stock__company_name'))
        .annotate(
            single_bets=Coalesce(Count('id'), 0),
            single_handle=Coalesce(Sum('amount_wagered'), Decimal("0.00")),
            single_payout=Coalesce(Sum('payout_amount'), Decimal("0.00")),
        )
    )

    # Aggregate parlays by inspecting legs -> parlay_bet.user and leg.market.stock
    # We'll annotate parlays grouped by the stock symbol of the leg's market (a single parlay may span multiple stocks;
    # this groups a parlay leg as contribution to that stock)
    parlay_leg_qs = Bet.objects.filter(is_parlay_leg=True, parlay_bet__isnull=False, market__isnull=False).select_related('market__stock', 'parlay_bet')
    if dt_from:
        parlay_leg_qs = parlay_leg_qs.filter(created_at__gte=dt_from)
    if dt_to:
        parlay_leg_qs = parlay_leg_qs.filter(created_at__lte=dt_to)

    parlay_by_stock = (
        parlay_leg_qs.values(stock_symbol=F('market__stock__symbol'))
        .annotate(
            parlay_legs=Coalesce(Count('id'), 0),
            parlay_handle=Coalesce(Sum('parlay_bet__amount_wagered'), Decimal("0.00")),  # may overcount if multiple legs per parlay -> careful
            parlay_payout=Coalesce(Sum('parlay_bet__payout_amount'), Decimal("0.00")),
        )
    )

    # Build a dict mapping symbol -> aggregated parlay sums (we'll handle potential overcounting by summing leg contributions conservatively)
    parlay_map = {}
    for r in parlay_by_stock:
        sym = r['stock_symbol']
        parlay_map[sym] = {
            'parlay_legs': int(r['parlay_legs']),
            'parlay_handle': _to_decimal(r['parlay_handle']),
            'parlay_payout': _to_decimal(r['parlay_payout']),
        }

    # Build final list merging bet_by_stock and parlay_map and adding market counts
    results = []
    # get list of all stocks (to include stocks with markets but no bets)
    stocks = Stock.objects.all().only('symbol', 'company_name')
    stock_index = {s.symbol: s for s in stocks}

    # Create initial entries from single bets aggregation
    handled_symbols = set()
    for row in bet_by_stock:
        sym = row['stock_symbol']
        if not sym:
            continue
        handled_symbols.add(sym)
        single_handle = _to_decimal(row['single_handle'])
        single_payout = _to_decimal(row['single_payout'])
        parlay = parlay_map.get(sym, {})
        parlay_handle = parlay.get('parlay_handle', Decimal("0.00"))
        parlay_payout = parlay.get('parlay_payout', Decimal("0.00"))

        total_handle = (single_handle + parlay_handle).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_payout = (single_payout + parlay_payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ggr = (total_handle - total_payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        hold_pct = Decimal("0.00")
        if total_handle:
            hold_pct = (ggr / total_handle * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        stock_obj = stock_index.get(sym)
        active_markets_count = Market.objects.filter(stock__symbol__iexact=sym, is_active=True).count()
        total_volume = Market.objects.filter(stock__symbol__iexact=sym).aggregate(t=Coalesce(Sum('total_volume'), 0))['t'] or 0

        results.append({
            'symbol': sym,
            'company_name': stock_obj.company_name if stock_obj else None,
            'single_bets': int(row['single_bets']),
            'parlay_legs': parlay.get('parlay_legs', 0),
            'handle': money_str(total_handle),
            'payout': money_str(total_payout),
            'ggr': money_str(ggr),
            'hold_percent': str(hold_pct),
            'active_markets': int(active_markets_count),
            'total_volume': int(total_volume),
        })

    # include stocks that had parlays but no single bets
    for sym, data in parlay_map.items():
        if sym in handled_symbols:
            continue
        parlay_handle = data.get('parlay_handle', Decimal("0.00"))
        parlay_payout = data.get('parlay_payout', Decimal("0.00"))
        total_handle = parlay_handle
        total_payout = parlay_payout
        ggr = (total_handle - total_payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        hold_pct = Decimal("0.00")
        if total_handle:
            hold_pct = (ggr / total_handle * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        stock_obj = stock_index.get(sym)
        active_markets_count = Market.objects.filter(stock__symbol__iexact=sym, is_active=True).count()
        total_volume = Market.objects.filter(stock__symbol__iexact=sym).aggregate(t=Coalesce(Sum('total_volume'), 0))['t'] or 0

        results.append({
            'symbol': sym,
            'company_name': stock_obj.company_name if stock_obj else None,
            'single_bets': 0,
            'parlay_legs': data.get('parlay_legs', 0),
            'handle': money_str(total_handle),
            'payout': money_str(total_payout),
            'ggr': money_str(ggr),
            'hold_percent': str(hold_pct),
            'active_markets': int(active_markets_count),
            'total_volume': int(total_volume),
        })

    # sort by handle descending
    results.sort(key=lambda x: Decimal(x['handle']), reverse=True)
    return results


def market_breakdown(stock_symbol: str, date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return list of markets for a stock with aggregated metrics per market:
    - market id, target_price, expiry_date, outcome_type
    - bets_count, handle, payout, ggr, implied odds (over/under), display odds
    """
    dt_from, dt_to = parse_date_range(date_from, date_to)

    market_qs = Market.objects.filter(stock__symbol__iexact=stock_symbol).select_related('stock')
    if dt_from:
        market_qs = market_qs.filter(created_at__gte=dt_from)
    if dt_to:
        market_qs = market_qs.filter(created_at__lte=dt_to)

    results = []
    for m in market_qs:
        # Aggregate bets belonging to this market
        bets = Bet.objects.filter(market=m)
        if dt_from:
            bets = bets.filter(created_at__gte=dt_from)
        if dt_to:
            bets = bets.filter(created_at__lte=dt_to)

        bet_agg = bets.aggregate(
            count=Coalesce(Count('id'), 0),
            handle=Coalesce(Sum('amount_wagered'), Decimal("0.00")),
            payout=Coalesce(Sum('payout_amount'), Decimal("0.00")),
        )

        # Also include parlay legs that reference this market (their parlay's amount_wagered contributes to parlay handle/payout)
        parlay_leg_qs = Bet.objects.filter(is_parlay_leg=True, market=m, parlay_bet__isnull=False)
        if dt_from:
            parlay_leg_qs = parlay_leg_qs.filter(created_at__gte=dt_from)
        if dt_to:
            parlay_leg_qs = parlay_leg_qs.filter(created_at__lte=dt_to)

        parlay_agg = parlay_leg_qs.aggregate(
            legs=Coalesce(Count('id'), 0),
            parlay_handle=Coalesce(Sum('parlay_bet__amount_wagered'), Decimal("0.00")),
            parlay_payout=Coalesce(Sum('parlay_bet__payout_amount'), Decimal("0.00")),
        )

        handle = _to_decimal(bet_agg['handle']) + _to_decimal(parlay_agg['parlay_handle'])
        payout = _to_decimal(bet_agg['payout']) + _to_decimal(parlay_agg['parlay_payout'])
        ggr = (handle - payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        hold_pct = Decimal("0.00")
        if handle:
            hold_pct = (ggr / handle * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        results.append({
            'market_id': m.id,
            'target_price': str(m.target_price),
            'expiry_date': m.expiry_date.isoformat() if m.expiry_date else None,
            'outcome_type': m.outcome_type,
            'bets_count': int(bet_agg['count'] or 0),
            'parlay_legs_count': int(parlay_agg['legs'] or 0),
            'handle': money_str(handle),
            'payout': money_str(payout),
            'ggr': money_str(ggr),
            'hold_percent': str(hold_pct),
            'implied_odds_over': str(m.implied_odds_over_rounded) if hasattr(m, 'implied_odds_over_rounded') else None,
            'implied_odds_under': str(m.implied_odds_under_rounded) if hasattr(m, 'implied_odds_under_rounded') else None,
            'display_odds_over': m.display_odds_over,
            'display_odds_under': m.display_odds_under,
            'is_active': m.is_active,
            'total_volume': m.total_volume,
        })

    # sort by expiry then target price
    results.sort(key=lambda x: (x['expiry_date'] or '', Decimal(x['target_price'])), reverse=False)
    return results
# ------------------------------
# User Analytics Function
# ------------------------------

def bets_feed(page=1, page_size=25, date_from=None, date_to=None, user=None, stock=None, status=None, search=None):
    """
    Returns paginated list of all bets (single + parlay) for the admin dashboard.
    Supports filters and includes 'type' field for frontend differentiation.
    """
    # ------------------------
    # 🧩 1️⃣ Single Bets
    # ------------------------
    bets_qs = Bet.objects.select_related("user", "market__stock").order_by("-created_at")

    if date_from:
        bets_qs = bets_qs.filter(created_at__date__gte=date_from)
    if date_to:
        bets_qs = bets_qs.filter(created_at__date__lte=date_to)
    if user:
        bets_qs = bets_qs.filter(user__username__icontains=user)
    if stock:
        bets_qs = bets_qs.filter(market__stock__symbol__icontains=stock)
    if status:
        bets_qs = bets_qs.filter(status__iexact=status)
    if search:
        bets_qs = bets_qs.filter(
            Q(user__username__icontains=search)
            | Q(market__stock__symbol__icontains=search)
        )

    single_bets = [
        {
            "id": bet.id,
            "type": "single",
            "user_id": bet.user.id,
            "username": bet.user.username,
            "stock_symbol": bet.market.stock.symbol if bet.market else None,
            "stock_id": bet.market.stock.id if bet.market else None,
            "amount_wagered": float(bet.amount_wagered or 0),
            "payout_amount": float(bet.payout_amount or 0),
            "potential_payout": float(bet.get_potential_payout() or 0),
            "status": bet.status,
            "created_at": bet.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for bet in bets_qs
    ]

    # ------------------------
    # 🧩 2️⃣ Parlay Bets
    # ------------------------
    parlay_qs = ParlayBet.objects.select_related("user").order_by("-created_at")

    if date_from:
        parlay_qs = parlay_qs.filter(created_at__date__gte=date_from)
    if date_to:
        parlay_qs = parlay_qs.filter(created_at__date__lte=date_to)
    if user:
        parlay_qs = parlay_qs.filter(user__username__icontains=user)
    if status:
        parlay_qs = parlay_qs.filter(status__iexact=status)
    if search:
        parlay_qs = parlay_qs.filter(user__username__icontains=search)

    parlay_bets = [
        {
            "id": pb.id,
            "type": "parlay",
            "user_id": pb.user.id,
            "username": pb.user.username,
            "stock_symbol": None,  # Parlays span multiple stocks
            "stock_id": None,
            "legs_count": pb.legs.count(),
            "amount_wagered": float(pb.amount_wagered or 0),
            "payout_amount": float(pb.payout_amount or 0),
            "potential_payout": float(pb.get_potential_payout() or 0),
            "combined_odds": pb.combined_odds,
            "status": pb.status,
            "created_at": pb.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for pb in parlay_qs
    ]

    # ------------------------
    # 🧩 3️⃣ Combine and Sort
    # ------------------------
    combined = single_bets + parlay_bets
    combined.sort(key=lambda x: x["created_at"], reverse=True)

    total = len(combined)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_results = combined[start:end]

    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": paginated_results,
    }

def market_analytics(stock_query: str = None, date_from=None, date_to=None) -> dict:
    """
    Aggregates market-level analytics grouped by asset (stock symbol) and expiry date.
    Ensures only markets that have actual bets are included.

    Returns a structure like:
    {
        "total_handle": 5609494.00,
        "total_payout": 5013800.00,
        "total_ggr": 595694.00,
        "market_summary": [
            {
                "asset": "TSLA",
                "company": "Tesla Inc.",
                "expiry_date": "2025-11-07",
                "num_bets": 12034,
                "handle": 5609494.00,
                "ggr": 595694.00,
                "hold_percent": 10.62
            },
            ...
        ]
    }
    """

    # Start from Bet (ensures only markets with activity)
    bets = Bet.objects.select_related("market__stock")

    # Optional filter by stock symbol or company name
    if stock_query:
        bets = bets.filter(
            Q(market__stock__symbol__icontains=stock_query)
            | Q(market__stock__company_name__icontains=stock_query)
        )

    # Optional date filters
    if date_from:
        bets = bets.filter(created_at__gte=date_from)
    if date_to:
        bets = bets.filter(created_at__lte=date_to)

    # Group by asset and expiry date
    summary_qs = (
        bets.values(
            "market__stock__symbol",
            "market__stock__company_name",
            "market__expiry_date",
        )
        .annotate(
            num_bets=Count("id", distinct=True),
            total_handle=Sum("amount_wagered", default=Decimal("0")),
            total_payout=Sum("payout_amount", default=Decimal("0")),
        )
        .order_by("market__stock__symbol", "market__expiry_date")
    )

    market_summary = []
    total_handle = Decimal("0")
    total_payout = Decimal("0")

    # Aggregate per group
    for s in summary_qs:
        handle = s["total_handle"] or Decimal("0")
        payout = s["total_payout"] or Decimal("0")
        ggr = handle - payout
        hold_percent = (ggr / handle * 100) if handle > 0 else Decimal("0")

        # Update totals
        total_handle += handle
        total_payout += payout

        # Append each row summary
        market_summary.append({
            "asset": s["market__stock__symbol"],
            "company": s["market__stock__company_name"],
            "expiry_date": (
                s["market__expiry_date"].strftime("%Y-%m-%d")
                if s["market__expiry_date"] else None
            ),
            "num_bets": int(s["num_bets"] or 0),
            "handle": handle.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "ggr": ggr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "hold_percent": hold_percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        })

    # Compute totals safely
    total_ggr = total_handle - total_payout

    return {
        "total_handle": total_handle.quantize(Decimal("0.01")),
        "total_payout": total_payout.quantize(Decimal("0.01")),
        "total_ggr": total_ggr.quantize(Decimal("0.01")),
        "market_summary": market_summary or [],
    }


def user_analytics(user_query=None, date_from=None, date_to=None):
    """
    Returns user-level analytics including single bets + parlay bets combined.
    Each user's total wager, payout, and GGR now factor in both.
    """

    users_qs = Profile.objects.select_related("user", "user__wallet", "user__kyc_profile")

    if user_query:
        users_qs = users_qs.filter(user__username__icontains=user_query)

    users_data = []
    for p in users_qs:
        user = p.user

        # ---- Single Bets ----
        bets = Bet.objects.filter(user=user)
        if date_from:
            bets = bets.filter(created_at__date__gte=date_from)
        if date_to:
            bets = bets.filter(created_at__date__lte=date_to)

        bet_wager = bets.aggregate(total=Coalesce(Sum("amount_wagered"), Decimal("0.00")))["total"]
        bet_payout = bets.aggregate(total=Coalesce(Sum("payout_amount"), Decimal("0.00")))["total"]

        # ---- Parlay Bets ----
        parlay_qs = ParlayBet.objects.filter(user=user)
        if date_from:
            parlay_qs = parlay_qs.filter(created_at__date__gte=date_from)
        if date_to:
            parlay_qs = parlay_qs.filter(created_at__date__lte=date_to)

        parlay_wager = parlay_qs.aggregate(total=Coalesce(Sum("amount_wagered"), Decimal("0.00")))["total"]
        parlay_payout = parlay_qs.aggregate(total=Coalesce(Sum("payout_amount"), Decimal("0.00")))["total"]

        # ---- Combine Both ----
        total_wager = bet_wager + parlay_wager
        total_payout = bet_payout + parlay_payout
        ggr_value = total_wager - total_payout
        total_bets_count = bets.count() + parlay_qs.count()

        try:
            balance = round_two_places(user.wallet.balance)
        except Wallet.DoesNotExist:
            balance = Decimal("0.00")
            
        try:
            kyc = user.kyc_profile
            kyc_status = kyc.kyc_status
        except Exception as e:
            kyc_status = None


        users_data.append({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "balance": balance,
            "crs_risk_score": p.crs_risk_score,
            "crs_risk_level": p.crs_risk_level,
            "max_wager_allowed": float(p.max_wager_allowed),
            "ggr": round_two_places(ggr_value),
            "total_wager": round_two_places(total_wager),
            "total_payout": round_two_places(total_payout),
            "bet_count": total_bets_count,
            "kyc_status": kyc_status
        })

    # ---- Sorting and Distribution ----
    users_sorted = sorted(users_data, key=lambda x: x["ggr"], reverse=True)
    crs_distribution = (
        users_qs.values("crs_risk_level").annotate(count=Count("id")).order_by("crs_risk_level")
    )

    return {
        "total_users": len(users_data),
        "crs_distribution": list(crs_distribution),
        "top_users": users_sorted[:5],
        "worst_users": users_sorted[-5:] if len(users_sorted) > 5 else [],
        "users": users_data
    }



# def bets_feed(
#     page: int = 1,
#     page_size: int = DEFAULT_PAGE_SIZE,
#     date_from: Optional[str] = None,
#     date_to: Optional[str] = None,
#     user: Optional[str] = None,
#     stock: Optional[str] = None,
#     status: Optional[str] = None,
#     search: Optional[str] = None,
#     ordering: str = '-created_at'
# ) -> Dict[str, Any]:
#     """
#     Paginated feed of Bet objects (both single bets and parlay legs).
#     Filtering:
#       - user: matches @username or full name (first + last),
#       - stock: matches stock symbol or company_name (case-insensitive, partial allowed),
#       - status: bet status,
#       - search: searches username, stock symbol, market target price, or odds
#     Returns a dict with count, page, page_size, num_pages, results[]
#     Each result contains normalized fields for frontend consumption.
#     """
#     dt_from, dt_to = parse_date_range(date_from, date_to)

#     qs = Bet.objects.select_related('user', 'market__stock').all()

#     # Date filters
#     if dt_from:
#         qs = qs.filter(created_at__gte=dt_from)
#     if dt_to:
#         qs = qs.filter(created_at__lte=dt_to)

#     # User filter -> support '@username' or full name
#     if user:
#         u = user.strip()
#         if u.startswith('@'):
#             u = u[1:]
#         user_q = Q(user__username__iexact=u) | Q(user__username__icontains=u)
#         if ' ' in u:
#             first, last = u.split(' ', 1)
#             user_q |= Q(user__first_name__iexact=first.strip(), user__last_name__iexact=last.strip())
#         qs = qs.filter(user_q)

#     # Stock filter -> symbol or company name
#     if stock:
#         s = stock.strip()
#         qs = qs.filter(Q(market__stock__symbol__iexact=s) | Q(market__stock__symbol__icontains=s) | Q(market__stock__company_name__icontains=s))

#     # status
#     if status:
#         qs = qs.filter(status__iexact=status)

#     # search
#     if search:
#         sq = search.strip()
#         qs = qs.filter(
#             Q(user__username__icontains=sq)
#             | Q(user__first_name__icontains=sq)
#             | Q(user__last_name__icontains=sq)
#             | Q(market__stock__symbol__icontains=sq)
#             | Q(market__stock__company_name__icontains=sq)
#             | Q(market__target_price__icontains=sq)
#             | Q(odds_at_placement__icontains=sq)
#         )

#     # ordering and pagination
#     qs = qs.order_by(ordering)

#     page_size = min(MAX_PAGE_SIZE, max(1, int(page_size or DEFAULT_PAGE_SIZE)))
#     paginator = Paginator(qs, page_size)
#     page_obj = paginator.get_page(page)

#     results = []
#     for b in page_obj:
#         market = getattr(b, 'market', None)
#         stock_obj = getattr(market, 'stock', None) if market else None
#         # potential fields for frontend
#         results.append({
#             'bet_id': b.id,
#             'created_at': b.created_at.isoformat() if b.created_at else None,
#             'is_parlay_leg': bool(b.is_parlay_leg),
#             'parlay_id': b.parlay_bet.id if b.parlay_bet else None,
#             'user_id': b.user.id if b.user else None,
#             'username': b.user.username if b.user else None,
#             'full_name': f"{b.user.first_name} {b.user.last_name}".strip() if b.user else None,
#             'stock_symbol': stock_obj.symbol if stock_obj else None,
#             'stock_name': stock_obj.company_name if stock_obj else None,
#             'market_id': market.id if market else None,
#             'target_price': str(market.target_price) if market else None,
#             'expiry_date': market.expiry_date.isoformat() if market and market.expiry_date else None,
#             'chosen_outcome': b.chosen_outcome,
#             'amount_wagered': money_str(b.amount_wagered),
#             'odds_at_placement': b.odds_at_placement,
#             'decimal_odds': str(b.decimal_odds) if hasattr(b, 'decimal_odds') else None,
#             'potential_payout': money_str(b.get_potential_payout() if hasattr(b, 'get_potential_payout') else None),
#             'payout_amount': money_str(b.payout_amount),
#             'status': b.status,
#             'settled_at': b.settled_at.isoformat() if b.settled_at else None,
#         })

#     return {
#         'count': paginator.count,
#         'page': page_obj.number,
#         'page_size': page_size,
#         'num_pages': paginator.num_pages,
#         'results': results,
#     }

