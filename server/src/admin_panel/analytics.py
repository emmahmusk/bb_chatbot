"""
admin_panel/analytics.py

Analytics helpers for Bets, Parlays, Markets and Stocks.

Assumptions:
- Models are available in `betengine.models` or `your_app.models` (adjust imports below).
- User profile is available via `user.profile` (Profile model provided).
- Decimal monetary fields: Bet.amount_wagered, Bet.payout_amount, ParlayBet.amount_wagered, ParlayBet.payout_amount.
- Market <-> Stock relation: Market.stock (FK to Stock).

All monetary values returned as strings (e.g. "123.45") to avoid JSON float rounding problems.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from datetime import datetime, time, timedelta, date

from django.db.models import (
    Sum, Count, F, Q, Value, Avg, Case, When, DecimalField, Max, CharField, ExpressionWrapper, Prefetch, OuterRef, Subquery
)
from django.db.models.functions import Coalesce, Concat
from django.core.paginator import Paginator, EmptyPage
from django.utils import timezone
from django.contrib.auth import get_user_model
# Replace 'betengine' with your real app name if different
from betengine.models import Bet, ParlayBet, Market, Stock
from collections import defaultdict
from .serializers import AdminBetSerializer
from user.models import Profile, Wallet  # adjust import path if your Profile lives elsewhere
User = get_user_model()
# increase decimal precision for intermediary calculations
getcontext().prec = 12

# ---------- Constants (tuneable) ----------
DEFAULT_EXPOSURE_LIMIT_CRS_1 = Decimal("500.00")  # baseline amount a CRS=1.0 user can win
MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE = 25



# CHETHAN START



def market_analytics_v2(
    status_filter: Literal["settled", "pending"],
    stock_query: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    v2 Multi-level Market Analytics used by /admin_panel/analytics/dashboard-new/.

    Same response shape as market_analytics(), but:
      - Uses the same date normalisation approach as overall_analytics_v2
      - For `settled` -> realized_ggr (handle - payout_amount)
      - For `pending` -> potential_ggr (handle - get_potential_payout())
    """

    if status_filter not in ["settled", "pending"]:
        raise ValueError("Invalid status_filter. Must be 'settled' or 'pending'.")

    today = timezone.now().date()

    # ---- Normalise date range to dates ----
    d_from = None
    d_to = None

    if not date_from and not date_to:
        d_from = today - timedelta(days=30)
        d_to = today
    else:
        if isinstance(date_from, date):
            d_from = date_from
        elif isinstance(date_from, str):
            try:
                d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                d_from = None

        if isinstance(date_to, date):
            d_to = date_to
        elif isinstance(date_to, str):
            try:
                d_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                d_to = None

        # If only one side is present, fill the other sensibly
        if d_from is None and d_to is not None:
            d_from = d_to - timedelta(days=30)
        if d_to is None and d_from is not None:
            d_to = today

        # Swap if reversed
        if d_from and d_to and d_from > d_to:
            d_from, d_to = d_to, d_from

    if d_from is None:
        d_from = today - timedelta(days=30)
    if d_to is None:
        d_to = today

    # Keep these as dates for returning in the payload
    date_from_obj = d_from
    date_to_obj = d_to

    # Build datetime range for settled filters
    date_from_dt = timezone.make_aware(datetime.combine(d_from, time.min))
    date_to_dt = timezone.make_aware(datetime.combine(d_to, time.max))

    # ---- Base queryset / status semantics ----
    bets = Bet.objects.select_related("market__stock")

    if status_filter == "settled":
        settled_statuses = ["won", "lost", "void"]
        bets = bets.filter(
            status__in=settled_statuses,
            settled_at__range=(date_from_dt, date_to_dt),
        )
        ggr_label = "realized_ggr"
        payout_source_function = None
        payout_field = "payout_amount"
    else:  # pending
        # Pending exposure as-of `d_to` (same idea as overall_analytics_v2)
        bets = bets.filter(
            status="pending",
            created_at__date__lte=d_to,
        )
        ggr_label = "potential_ggr"
        payout_source_function = "get_potential_payout"
        payout_field = None

    # ---- Optional stock filter ----
    if stock_query:
        bets = bets.filter(
            Q(market__stock__symbol__icontains=stock_query)
            | Q(market__stock__company_name__icontains=stock_query)
        )

    # ---- Aggregation skeleton ----
    data = defaultdict(lambda: {"totals": {}, "expiries": defaultdict(dict)})

    for bet in bets:
        market = bet.market
        stock = market.stock if (market and market.stock) else None

        # Skip bets without a proper asset
        if not stock or not stock.symbol:
            continue

        ticker = stock.symbol
        expiry_key = (
            market.expiry_date.strftime("%Y-%m-%d")
            if market and market.expiry_date
            else "Unknown"
        )

        strike_dec = _to_decimal(market.target_price or 0) if market else Decimal("0.00")
        outcome = (bet.chosen_outcome or "-").capitalize()
        status_label = (bet.status or status_filter).capitalize()

        group_key = f"{outcome} ${strike_dec} | {status_label}"

        handle = _to_decimal(bet.amount_wagered or 0)

        # Pick payout based on settled/pending
        if payout_source_function:
            try:
                payout_raw = getattr(bet, payout_source_function)()
            except Exception:
                payout_raw = Decimal("0.00")
            payout = _to_decimal(payout_raw)
        else:
            payout = _to_decimal(getattr(bet, payout_field) or 0)

        asset_entry = data[ticker]
        expiry_entry = asset_entry["expiries"][expiry_key]

        if "groups" not in expiry_entry:
            expiry_entry["groups"] = defaultdict(
                lambda: {
                    "num_bets": 0,
                    "handle": Decimal("0.00"),
                    "payout": Decimal("0.00"),
                }
            )

        grp = expiry_entry["groups"][group_key]
        grp["num_bets"] += 1
        grp["handle"] += handle
        grp["payout"] += payout

    # ---- Build final nested structure ----
    output_data: Dict[str, Any] = {}

    for ticker, ticker_entry in data.items():
        total_bets_asset = 0
        total_handle_asset = Decimal("0.00")
        total_payout_asset = Decimal("0.00")

        # Sort expiries: most recent first, "Unknown" last
        sorted_expiries = sorted(
            ticker_entry["expiries"].keys(),
            key=lambda d: (d != "Unknown", d),
            reverse=True,
        )

        new_expiry_dict: Dict[str, Any] = {}

        for expiry in sorted_expiries:
            expiry_data = ticker_entry["expiries"][expiry]
            group_rows: List[Dict[str, Any]] = []

            total_bets_expiry = 0
            total_handle_expiry = Decimal("0.00")
            total_payout_expiry = Decimal("0.00")

            for gkey, gvals in expiry_data["groups"].items():
                handle = gvals["handle"]
                payout = gvals["payout"]

                ggr = (handle - payout).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

                if handle > 0:
                    hold_pct = (ggr / handle * Decimal("100")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                else:
                    hold_pct = Decimal("0.00")

                group_rows.append(
                    {
                        "group": gkey,
                        "num_bets": gvals["num_bets"],
                        "handle": money_str(handle),
                        ggr_label: money_str(ggr),
                        "hold_percent": f"{hold_pct}%",
                    }
                )

                total_bets_expiry += gvals["num_bets"]
                total_handle_expiry += handle
                total_payout_expiry += payout

            ggr_expiry = (total_handle_expiry - total_payout_expiry).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if total_handle_expiry > 0:
                hold_expiry = (ggr_expiry / total_handle_expiry * Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                hold_expiry = Decimal("0.00")

            expiry_totals = {
                "num_bets": total_bets_expiry,
                "handle": money_str(total_handle_expiry),
                ggr_label: money_str(ggr_expiry),
                "hold_percent": f"{hold_expiry}%",
            }

            new_expiry_dict[expiry] = {
                "totals": expiry_totals,
                "groups": group_rows,
            }

            total_bets_asset += total_bets_expiry
            total_handle_asset += total_handle_expiry
            total_payout_asset += total_payout_expiry

        ggr_asset = (total_handle_asset - total_payout_asset).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if total_handle_asset > 0:
            hold_asset = (ggr_asset / total_handle_asset * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            hold_asset = Decimal("0.00")

        asset_totals = {
            "num_bets": total_bets_asset,
            "handle": money_str(total_handle_asset),
            ggr_label: money_str(ggr_asset),
            "hold_percent": f"{hold_asset}%",
        }

        output_data[ticker] = {
            "totals": asset_totals,
            "expiries": new_expiry_dict,
        }

    return {
        "status_filter": status_filter,
        "date_filter": {
            "from": date_from_obj.strftime("%Y-%m-%d") if date_from_obj else None,
            "to": date_to_obj.strftime("%Y-%m-%d") if date_to_obj else None,
        },
        "data": output_data,
    }


def overall_analytics_v2(
    date_from=None,
    date_to=None,
    status_filter: str = "all",
    active_only: bool = False,
) -> dict:
    """
    v2 Overall analytics for /admin_panel/analytics/dashboard-new/

    Goals:
      - Same JSON shape as old overall_analytics()
      - Accurate filters:
          * status_filter: "all" | "pending" | "settled"
          * date_from / date_to: inclusive date window
          * active_only: restrict to bettors active in last 30 days
      - Works with both Bet and ParlayBet.
    """

    today = timezone.now().date()

    # --- Normalise date range into date objects ---
    if not date_from and not date_to:
        date_from = today - timedelta(days=30)
        date_to = today

    if isinstance(date_from, str):
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
    if isinstance(date_to, str):
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

    if date_from > date_to:
        date_from, date_to = date_to, date_from

    date_from_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, time.max))

    # --- Normalise status_filter ---
    status_norm = (status_filter or "all").lower().strip()
    if status_norm not in ("all", "pending", "settled"):
        status_norm = "all"

    # --- Base querysets ---
    bets_qs = Bet.objects.select_related("user")
    parlay_qs = ParlayBet.objects.select_related("user")

    # --- Active / inactive user logic (unchanged semantics) ---
    active_users_count, inactive_users_count, active_ids = get_active_inactive_users()
    if active_only:
        bets_qs = bets_qs.filter(user__id__in=active_ids)
        parlay_qs = parlay_qs.filter(user__id__in=active_ids)

    # --- Apply status/time filters consistently ---
    if status_norm == "all":
        # Bets that are either pending or settled in the window
        bets_qs = bets_qs.filter(
            Q(status="pending")
            | Q(settled_at__range=(date_from_dt, date_to_dt))
        )
        parlay_qs = parlay_qs.filter(
            Q(status="pending")
            | Q(settled_at__range=(date_from_dt, date_to_dt))
        )

    elif status_norm == "pending":
        # Still open as of date_to
        bets_qs = bets_qs.filter(
            status="pending",
            created_at__date__lte=date_to,
        )
        parlay_qs = parlay_qs.filter(
            status="pending",
            created_at__date__lte=date_to,
        )

    elif status_norm == "settled":
        # Actually settled in the window
        settled_statuses = ["won", "lost", "void"]
        bets_qs = bets_qs.filter(
            status__in=settled_statuses,
            settled_at__range=(date_from_dt, date_to_dt),
        )
        parlay_qs = parlay_qs.filter(
            status__in=settled_statuses,
            settled_at__range=(date_from_dt, date_to_dt),
        )

    total_bets_count = bets_qs.count() + parlay_qs.count()

    # --- Base result skeleton (same keys as old one, plus more) ---
    result = {
        "date_range": {
            "from": date_from.strftime("%Y-%m-%d"),
            "to": date_to.strftime("%Y-%m-%d"),
        },
        "status_filter": status_norm,
        "active_only": bool(active_only),
        "last_updated": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_bets_count": total_bets_count,
    }

    # ---------- Settled metrics block ----------
    if status_norm in ("settled", "all"):
        settled_statuses = ["won", "lost", "void"]

        settled_bets_qs = bets_qs.filter(
            status__in=settled_statuses,
            settled_at__range=(date_from_dt, date_to_dt),
        )
        settled_parlay_qs = parlay_qs.filter(
            status__in=settled_statuses,
            settled_at__range=(date_from_dt, date_to_dt),
        )

        settled_bet_agg = settled_bets_qs.aggregate(
            wager=Coalesce(Sum("amount_wagered"), Decimal("0.00")),
            payout=Coalesce(Sum("payout_amount"), Decimal("0.00")),
        )
        settled_parlay_agg = settled_parlay_qs.aggregate(
            wager=Coalesce(Sum("amount_wagered"), Decimal("0.00")),
            payout=Coalesce(Sum("payout_amount"), Decimal("0.00")),
        )

        total_wager_settled = settled_bet_agg["wager"] + settled_parlay_agg["wager"]
        total_payout_settled = settled_bet_agg["payout"] + settled_parlay_agg["payout"]
        settled_ggr = total_wager_settled - total_payout_settled
        hold_pct_settled = calculate_hold_percent(settled_ggr, total_wager_settled)

        result.update(
            {
                "settled_ggr": round_two_places(settled_ggr),
                "total_wager_settled": round_two_places(total_wager_settled),
                "total_payout_settled": round_two_places(total_payout_settled),
                "hold_percent_settled": hold_pct_settled,
            }
        )
    else:
        # Keep keys so FE doesn’t blow up when status = pending
        result.update(
            {
                "settled_ggr": None,
                "total_wager_settled": None,
                "total_payout_settled": None,
                "hold_percent_settled": None,
            }
        )

    # ---------- Pending metrics block ----------
    if status_norm in ("pending", "all"):
        pending_bets_qs = bets_qs.filter(status="pending")
        pending_parlay_qs = parlay_qs.filter(status="pending")

        total_pending_wager = (
            pending_bets_qs.aggregate(
                total=Coalesce(Sum("amount_wagered"), Decimal("0.00"))
            )["total"]
            + pending_parlay_qs.aggregate(
                total=Coalesce(Sum("amount_wagered"), Decimal("0.00"))
            )["total"]
        )

        total_pending_payout = Decimal("0.00")
        for bet in pending_bets_qs:
            total_pending_payout += bet.get_potential_payout() or Decimal("0.00")
        for pb in pending_parlay_qs:
            total_pending_payout += pb.get_potential_payout() or Decimal("0.00")

        pending_ggr = total_pending_wager - total_pending_payout
        hold_pct_pending = calculate_hold_percent(pending_ggr, total_pending_wager)

        result.update(
            {
                "total_wager_pending": round_two_places(total_pending_wager),
                "total_payout_pending": round_two_places(total_pending_payout),
                "potential_ggr": round_two_places(pending_ggr),
                "hold_percent_pending": hold_pct_pending,
            }
        )
    else:
        result.update(
            {
                "total_wager_pending": None,
                "total_payout_pending": None,
                "potential_ggr": None,
                "hold_percent_pending": None,
            }
        )

    # ---------- User metrics (top/worst) ----------
    top_users = get_top_users_by_ggr(
        start_date=date_from,
        end_date=date_to,
        status_filter=status_norm,
        top_n=5,
        include_parlays=True,
    )
    worst_users = get_top_users_by_ggr(
        start_date=date_from,
        end_date=date_to,
        status_filter=status_norm,
        top_n=5,
        reverse=True,
        include_parlays=True,
    )

    result.update(
        {
            "active_users": active_users_count,
            "inactive_users": inactive_users_count,
            "top_users": top_users,
            "worst_users": worst_users,
        }
    )

    return result


def normalize_date_inputs(
    date_from: Optional[str],
    date_to: Optional[str],
    default_days: int = 30,
) -> Tuple[str, str]:
    """
    Ensures we always have a sane (from, to) date range.
    - Defaults to last `default_days` days ending today.
    - Swaps if from > to (helps if FE sends reversed).
    """
    today = timezone.now().date()

    if not date_from and not date_to:
        d_to = today
        d_from = today - timezone.timedelta(days=default_days)
    elif date_from and date_to:
        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            d_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            d_to = today
            d_from = today - timezone.timedelta(days=default_days)
        if d_from > d_to:
            d_from, d_to = d_to, d_from
    elif date_from and not date_to:
        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            d_from = today - timezone.timedelta(days=default_days)
        d_to = today
        if d_from > d_to:
            d_from, d_to = d_to, d_from
    else:  # only date_to
        try:
            d_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            d_to = today
        d_from = d_to - timezone.timedelta(days=default_days)
        if d_from > d_to:
            d_from, d_to = d_to, d_from

    return d_from.isoformat(), d_to.isoformat()


def bets_feed_v2(
    page=1,
    page_size=25,
    date_from=None,
    date_to=None,
    user=None,
    stock=None,
    status=None,
    search=None,
):
    """
    New bets feed for /analytics/dashboard-new/.

    - Same payload shape as old bets_feed()
    - Uses:
        * settled_at__date when status in (settled, won, lost, void)
        * created_at__date otherwise (pending / all)
    """

    queryset = (
        Bet.objects
        .select_related("user", "market__stock")
        .order_by("-created_at")
    )

    status_norm = (status or "").lower().strip()

    # Choose date field based on status
    if status_norm in ["settled", "won", "lost", "void"]:
        date_field = "settled_at__date"
    else:
        date_field = "created_at__date"

    # Date range
    if date_from:
        queryset = queryset.filter(**{f"{date_field}__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{date_field}__lte": date_to})

    # User / Stock filters
    if user:
        queryset = queryset.filter(user__username__icontains=user)
    if stock:
        queryset = queryset.filter(market__stock__symbol__icontains=stock)

    # Status filter
    if status_norm:
        if status_norm == "pending":
            queryset = queryset.filter(status__iexact="pending")
        elif status_norm == "won":
            queryset = queryset.filter(status__iexact="won")
        elif status_norm == "lost":
            queryset = queryset.filter(status__iexact="lost")
        elif status_norm == "void":
            queryset = queryset.filter(status__iexact="void")
        elif status_norm == "settled":
            queryset = queryset.filter(status__in=["won", "lost", "void"])
        elif status_norm != "all":
            queryset = queryset.filter(status__iexact=status_norm)

    # Search filter
    if search:
        queryset = queryset.filter(
            Q(user__username__icontains=search)
            | Q(market__stock__symbol__icontains=search)
            | Q(chosen_outcome__icontains=search)
        )

    # Pagination
    paginator = Paginator(queryset, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    serializer = AdminBetSerializer(page_obj, many=True)

    return {
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page_obj.number,
        "page_size": page_size,
        "results": serializer.data,
    }


## CHETHAN END


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


# ---------- REPLACED: market_analytics ----------
def market_analytics(
    status_filter: Literal["settled", "pending"],
    stock_query: Optional[str] = None, 
    date_from: Optional[str] = None, 
    date_to: Optional[str] = None
) -> dict:
    """
    Multi-level Market Analytics, filtered by status.
    Calculates GGR from the operator's perspective (Handle - Payout).
    
    Level 1: Asset totals (AAPL, TSLA, etc.)
    Level 2: Expiry-level breakdown per asset.
    Level 3: Outcome/strike/status groups under each expiry.
    """
    
    if status_filter not in ["settled", "pending"]:
        raise ValueError("Invalid status_filter. Must be 'settled' or 'pending'.")

    dt_from, dt_to = parse_date_range(date_from, date_to)

    # --- 1. Setup Status and Date Filters ---
    if status_filter == "settled":
        status_kwargs = {"status__in": ["won", "lost", "void"]}
        date_field = "settled_at"
        payout_key = "payout_amount"
        ggr_label = "realized_ggr"
        payout_source_function = None # Use static field
    else:
        status_kwargs = {"status": "pending"}
        date_field = "created_at"
        payout_key = "potential_payout"
        ggr_label = "potential_ggr"
        payout_source_function = 'get_potential_payout' # Use dynamic function

    date_kwargs = {}
    if dt_from:
        date_kwargs[f"{date_field}__gte"] = dt_from
    if dt_to:
        date_kwargs[f"{date_field}__lte"] = dt_to
        
    final_filter_kwargs = {**status_kwargs, **date_kwargs}

    # --- 2. Build QuerySet ---
    bets = Bet.objects.select_related("market__stock").filter(**final_filter_kwargs)

    if stock_query:
        bets = bets.filter(
            Q(market__stock__symbol__icontains=stock_query)
            | Q(market__stock__company_name__icontains=stock_query)
        )

    # --- 3. Initialize Data Structure ---
    data = defaultdict(lambda: {"totals": {}, "expiries": defaultdict(dict)})

    # --- 4. Safely iterate and Aggregate ---
    for bet in bets:
        # Edge Case: Skip bets missing core relational data
        if not bet.market or not bet.market.stock:
            continue

        ticker = bet.market.stock.symbol
        expiry_date = (
            bet.market.expiry_date.strftime("%Y-%m-%d")
            if bet.market.expiry_date else "Unknown"
        )
        strike = Decimal(bet.market.target_price or 0)
        outcome = bet.chosen_outcome.capitalize() if bet.chosen_outcome else "-"
        status = (bet.status or "pending").capitalize()

        # Level 3 group key
        group_key = f"{outcome} ${strike} | {status}"

        # Get Payout based on status filter
        handle = Decimal(bet.amount_wagered or 0)
        
        if payout_source_function:
            # For 'pending', call the method to get dynamic potential payout
            payout = getattr(bet, payout_source_function)() or Decimal("0.00")
        else:
            # For 'settled', use the static field
            payout = Decimal(getattr(bet, payout_key) or 0)

        # --- Ensure base keys exist & Aggregate ---
        asset_entry = data[ticker]
        expiry_entry = asset_entry["expiries"][expiry_date]
        if "groups" not in expiry_entry:
            expiry_entry["groups"] = defaultdict(lambda: {
                "num_bets": 0,
                "handle": Decimal("0.00"),
                "payout": Decimal("0.00"),
            })

        expiry_entry["groups"][group_key]["num_bets"] += 1
        expiry_entry["groups"][group_key]["handle"] += handle
        expiry_entry["groups"][group_key]["payout"] += payout # Uses calculated payout

    # --- 5. Compute Totals and Format Output ---
    output_data = {}
    
    for ticker, ticker_entry in data.items():
        total_bets_asset = 0
        total_handle_asset = Decimal("0.00")
        total_payout_asset = Decimal("0.00")

        # Sort expiries: most recent first (Unknown last)
        sorted_expiries = sorted(
            ticker_entry["expiries"].keys(),
            key=lambda d: (d != "Unknown", d),
            reverse=True
        )

        new_expiry_dict = {}
        for expiry in sorted_expiries:
            expiry_data = ticker_entry["expiries"][expiry]
            group_rows = []

            total_bets_expiry = 0
            total_handle_expiry = Decimal("0.00")
            total_payout_expiry = Decimal("0.00")

            # Format Groups
            for gkey, gvals in expiry_data["groups"].items():
                handle = gvals["handle"]
                payout = gvals["payout"]
                ggr = (handle - payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                hold_pct = Decimal("0.00")
                if handle > 0:
                    hold_pct = (ggr / handle * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                group_rows.append({
                    "group": gkey,
                    "num_bets": gvals["num_bets"],
                    "handle": money_str(handle),
                    ggr_label: money_str(ggr),
                    "hold_percent": f"{hold_pct}%",
                })

                total_bets_expiry += gvals["num_bets"]
                total_handle_expiry += handle
                total_payout_expiry += payout

            # Expiry-level totals
            ggr_expiry = (total_handle_expiry - total_payout_expiry).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            hold_expiry = Decimal("0.00")
            if total_handle_expiry > 0:
                hold_expiry = (ggr_expiry / total_handle_expiry * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            expiry_totals = {
                "num_bets": total_bets_expiry,
                "handle": money_str(total_handle_expiry),
                ggr_label: money_str(ggr_expiry),
                "hold_percent": f"{hold_expiry}%",
            }

            new_expiry_dict[expiry] = {
                "totals": expiry_totals,
                "groups": group_rows
            }

            total_bets_asset += total_bets_expiry
            total_handle_asset += total_handle_expiry
            total_payout_asset += total_payout_expiry

        # Asset-level totals
        ggr_asset = (total_handle_asset - total_payout_asset).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        hold_asset = Decimal("0.00")
        if total_handle_asset > 0:
            hold_asset = (ggr_asset / total_handle_asset * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        asset_totals = {
            "num_bets": total_bets_asset,
            "handle": money_str(total_handle_asset),
            ggr_label: money_str(ggr_asset),
            "hold_percent": f"{hold_asset}%"
        }

        output_data[ticker] = {
            "totals": asset_totals,
            "expiries": new_expiry_dict
        }

    # --- Final Output ---
    return {
        "status_filter": status_filter,
        "date_filter": {
            "from": dt_from.strftime("%Y-%m-%d") if dt_from else None,
            "to": dt_to.strftime("%Y-%m-%d") if dt_to else None,
        },
        "data": output_data
    }

# ---------- REPLACED: market_breakdown ----------
def market_breakdown(stock_symbol: str, date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    For a given stock symbol, return a breakdown by market (strike price / target_price and expiry date).
    Each row mirrors the "Asset drill-down" from the PDF:
      - asset, expiry_date, strike_price (market.target_price), num_bets, handle, ggr, hold_percent
    Includes both single bets and parlay legs' contributions. Monetary values are strings.
    """
    dt_from, dt_to = parse_date_range(date_from, date_to)

    # ensure symbol match is case-insensitive
    market_qs = Market.objects.filter(stock__symbol__iexact=stock_symbol)

    if dt_from:
        market_qs = market_qs.filter(created_at__gte=dt_from)
    if dt_to:
        market_qs = market_qs.filter(created_at__lte=dt_to)

    # We'll iterate markets and aggregate bets + parlay legs per market
    results = []
    for m in market_qs.order_by("expiry_date", "target_price"):
        # single bets for this market
        bets = Bet.objects.filter(market=m)
        if dt_from:
            bets = bets.filter(created_at__gte=dt_from)
        if dt_to:
            bets = bets.filter(created_at__lte=dt_to)

        bet_agg = bets.aggregate(
            count=Coalesce(Count("id"), 0),
            handle=Coalesce(Sum("amount_wagered"), Decimal("0.00")),
            payout=Coalesce(Sum("payout_amount"), Decimal("0.00")),
        )

        # parlay legs referencing this market (each leg belongs to a ParlayBet)
        parlay_leg_qs = Bet.objects.filter(is_parlay_leg=True, market=m, parlay_bet__isnull=False)
        if dt_from:
            parlay_leg_qs = parlay_leg_qs.filter(created_at__gte=dt_from)
        if dt_to:
            parlay_leg_qs = parlay_leg_qs.filter(created_at__lte=dt_to)

        parlay_agg = parlay_leg_qs.aggregate(
            legs=Coalesce(Count("id"), 0),
            # We sum using the parlay_bet's amount/payout; note: the same parlay can have multiple legs -> may cause double counting.
            parlay_handle=Coalesce(Sum("parlay_bet__amount_wagered"), Decimal("0.00")),
            parlay_payout=Coalesce(Sum("parlay_bet__payout_amount"), Decimal("0.00")),
        )

        handle = (_to_decimal(bet_agg["handle"]) + _to_decimal(parlay_agg["parlay_handle"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        payout = (_to_decimal(bet_agg["payout"]) + _to_decimal(parlay_agg["parlay_payout"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ggr = (handle - payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        hold_pct = Decimal("0.00")
        if handle and handle != Decimal("0"):
            hold_pct = (ggr / handle * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        results.append({
            "asset": m.stock.symbol if m.stock else stock_symbol,
            "expiry_date": m.expiry_date.strftime("%Y-%m-%d") if m.expiry_date else None,
            "strike_price": str(m.target_price) if m.target_price is not None else None,
            "num_bets": int(bet_agg["count"] or 0),
            "parlay_legs": int(parlay_agg["legs"] or 0),
            "handle": money_str(handle),
            "payout": money_str(payout),
            "ggr": money_str(ggr),
            "hold_percent": str(hold_pct),
        })

    # Sort results same as PDF: by expiry_date then strike_price (both ascending)
    results.sort(key=lambda r: (r["expiry_date"] or "", Decimal(r["strike_price"]) if r["strike_price"] else Decimal("0")))
    return results


# ---------- REPLACED: bets_feed (UPDATED GGR LOGIC) ----------

def bets_feed(page=1, page_size=25, date_from=None, date_to=None, user=None, stock=None, status=None, search=None):
    """
    Returns paginated and serialized bets feed for admin analytics dashboard.
    Filters bets by date, user, stock, status, and search query.
    Includes max_wager_pct and other computed fields from AdminBetSerializer.

    Status filter categories supported:
      - "pending" : only pending bets
      - "won"     : only won bets
      - "lost"    : only lost bets
      - "void"    : only voided bets
      - "settled" : bets that are won, lost, or void
      - "all" or None : no filter (all bets)
    """

    # ---- Base queryset ----
    queryset = Bet.objects.select_related("user", "market__stock").order_by("-created_at")

    # ---- Date filters ----
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    # ---- User / Stock filters ----
    if user:
        queryset = queryset.filter(user__username__icontains=user)
    if stock:
        queryset = queryset.filter(market__stock__symbol__icontains=stock)

    # ---- Status filter (includes logical category mapping) ----
    if status:
        status = status.lower().strip()
        if status == "pending":
            queryset = queryset.filter(status__iexact="pending")
        elif status == "won":
            queryset = queryset.filter(status__iexact="won")
        elif status == "lost":
            queryset = queryset.filter(status__iexact="lost")
        elif status == "void":
            queryset = queryset.filter(status__iexact="void")
        elif status == "settled":
            # Settled = all completed bets (not pending)
            queryset = queryset.filter(status__in=["won", "lost", "void"])
        elif status != "all":
            # Fallback: match direct string if not one of above
            queryset = queryset.filter(status__iexact=status)

    # ---- Search filter (username, ticker, outcome) ----
    if search:
        queryset = queryset.filter(
            Q(user__username__icontains=search)
            | Q(market__stock__symbol__icontains=search)
            | Q(chosen_outcome__icontains=search)
        )

    # ---- Pagination ----
    paginator = Paginator(queryset, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # ---- Serialize ----
    serializer = AdminBetSerializer(page_obj, many=True)

    # ---- Response payload ----
    return {
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page_obj.number,
        "page_size": page_size,
        "results": serializer.data,
    }
# def bets_feed(page=1, page_size=25, date_from=None, date_to=None, user=None, stock=None, status=None, search=None):
#     """
#     Paginated list of bets (singles + parlays) used in the Bets Feed UI.
    
#     Returns rows that include:
#       - bet_time, patron (username), crs, bet_id (Bet.id or ParlayBet.id), category,
#         asset, selection (Expiry | Strike), wager, odds_decimal, implied_percent, max_potential, ggr, status
#     """
#     dt_from, dt_to = parse_date_range(date_from, date_to)

#     # ------------------------
#     # Single bets
#     # ------------------------
#     single_qs = Bet.objects.select_related("user", "market__stock", "user__profile").order_by("-created_at")
    
#     if dt_from:
#         single_qs = single_qs.filter(created_at__gte=dt_from)
#     if dt_to:
#         single_qs = single_qs.filter(created_at__lte=dt_to)
#     if user:
#         single_qs = single_qs.filter(user__username__icontains=user)
#     if stock:
#         single_qs = single_qs.filter(market__stock__symbol__icontains=stock)
#     if status:
#         single_qs = single_qs.filter(status__iexact=status)
#     if search:
#         single_qs = single_qs.filter(
#             Q(user__username__icontains=search)
#             | Q(market__stock__symbol__icontains=search)
#         )

#     single_bets = []
#     for bet in single_qs:
#         # Selection text processing
#         selection = None
#         if getattr(bet, "market", None):
#             stock_symbol = bet.market.stock.symbol if bet.market.stock else None
#             expiry = bet.market.expiry_date.strftime("%Y-%m-%d") if bet.market.expiry_date else None
#             strike = f"${bet.market.target_price}" if bet.market.target_price is not None else None
#             outcome = getattr(bet.market, "outcome_type", None)
#             parts = [p for p in [stock_symbol, expiry] if p]
#             sel_right = " ".join([p for p in [outcome, strike] if p])
#             selection = f"{' '.join(parts)} | {sel_right}" if parts else sel_right

#         # Odds and implied probability calculation
#         american = bet.odds_at_placement
#         dec_odds = american_to_decimal(american) if american is not None else None
#         implied_pct = None
#         if dec_odds and dec_odds != Decimal("0"):
#             try:
#                 implied_pct = (Decimal("1.00") / dec_odds * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
#             except Exception:
#                 implied_pct = None

#         # Potential payout calculation
#         potential = None
#         try:
#             potential_val = bet.get_potential_payout() if hasattr(bet, "get_potential_payout") else None
#             potential = money_str(potential_val) if potential_val is not None else None
#         except Exception:
#             potential = None

#         # GGR calculation (Wager - Payout or Potential Loss)
#         wager = _to_decimal(bet.amount_wagered)
#         payout = _to_decimal(bet.payout_amount)
        
#         ggr_val = Decimal("0.00")
        
#         if bet.status in ['won', 'lost', 'void']:
#             # Settled GGR: Wager - Payout
#             ggr_val = (wager - payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
#         else: # Pending GGR: Wager - Potential Payout (Potential Loss)
#             try:
#                 pot = _to_decimal(bet.get_potential_payout()) if hasattr(bet, "get_potential_payout") else Decimal("0.00")
#                 ggr_val = (wager - pot).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
#             except Exception:
#                 ggr_val = Decimal("0.00")

#         # Fetch CRS score
#         crs_value = getattr(getattr(bet.user, "profile", None), "crs_risk_score", None)
#         if not selection:
#             continue

#         single_bets.append({
#             "bet_time": bet.created_at.strftime("%Y-%m-%d %H:%M:%S"),
#             "patron": bet.user.username if bet.user else None,
#             "crs": crs_value,
#             "bet_id": bet.id,
#             "category": "single",
#             "asset": bet.market.stock.symbol if getattr(bet, "market", None) and bet.market.stock else None,
#             "selection": selection,
#             "wager": money_str(wager),
#             "odds_decimal": str(dec_odds) if dec_odds is not None else None,
#             "potential_payout": potential,
#             "potential_ggr": money_str(ggr_val),
#             "status": getattr(bet, "status", None),
#         })

#     # ------------------------
#     # Parlay bets
#     # ------------------------
#     parlay_qs = ParlayBet.objects.select_related("user", "user__profile").order_by("-created_at")
    
#     if dt_from:
#         parlay_qs = parlay_qs.filter(created_at__gte=dt_from)
#     if dt_to:
#         parlay_qs = parlay_qs.filter(created_at__lte=dt_to)
#     if user:
#         parlay_qs = parlay_qs.filter(user__username__icontains=user)
#     if status:
#         parlay_qs = parlay_qs.filter(status__iexact=status)
#     if search:
#         parlay_qs = parlay_qs.filter(user__username__icontains=search)

#     parlay_bets = []
#     for pb in parlay_qs:
#         # Selection summary processing
#         try:
#             legs = pb.legs.all()
#         except Exception:
#             legs = []
#         legs_summ = []
#         for leg in legs[:4]:
#             try:
#                 leg_stock = leg.market.stock.symbol if getattr(leg, "market", None) and leg.market.stock else None
#                 leg_exp = leg.market.expiry_date.strftime("%Y-%m-%d") if getattr(leg, "market", None) and leg.market.expiry_date else None
#                 leg_str = f"{leg_stock} {leg_exp} | {getattr(leg.market, 'outcome_type', '')} ${getattr(leg.market, 'target_price', '')}"
#                 legs_summ.append(leg_str)
#             except Exception:
#                 continue
#         selection = "; ".join(legs_summ) if legs_summ else None

#         # Wager/Payout/GGR calculation
#         wager = _to_decimal(pb.amount_wagered)
#         payout = _to_decimal(pb.payout_amount)
        
#         ggr_val = Decimal("0.00")

#         if pb.status in ['won', 'lost', 'void']:
#             # Settled GGR: Wager - Payout
#             ggr_val = (wager - payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
#         else: # Pending GGR: Wager - Potential Payout (Potential Loss)
#             try:
#                 pot = _to_decimal(pb.get_potential_payout()) if hasattr(pb, "get_potential_payout") else Decimal("0.00")
#                 ggr_val = (wager - pot).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
#             except Exception:
#                 ggr_val = Decimal("0.00")

#         # Fetch CRS score
#         crs_value = getattr(getattr(pb.user, "profile", None), "crs_risk_score", None)
#         if "None" in selection:
#             continue
#         parlay_bets.append({
#             "bet_time": pb.created_at.strftime("%Y-%m-%d %H:%M:%S"),
#             "patron": pb.user.username if pb.user else None,
#             "crs": crs_value,
#             "bet_id": pb.id,
#             "category": "parlay",
#             "asset": None,
#             "selection": selection,
#             "legs_count": pb.legs.count() if hasattr(pb, "legs") else None,
#             "wager": money_str(wager),
#             "odds_decimal": round(pb.get_combined_decimal_odds()),
#             "potential_payout": money_str(pb.get_potential_payout()) if hasattr(pb, "get_potential_payout") else None,
#             "potential_ggr": money_str(ggr_val),
#             "status": getattr(pb, "status", None),
#         })

#     # Combine and paginate
#     combined = single_bets + parlay_bets
#     combined.sort(key=lambda x: x["bet_time"], reverse=True)

#     total = len(combined)
#     # clamp page_size
#     page_size = min(page_size or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
#     start = (page - 1) * page_size
#     end = start + page_size
#     paginated_results = combined[start:end]

#     return {
#         "count": total,
#         "page": page,
#         "page_size": page_size,
#         "results": paginated_results,
#     }

def calculate_asset_risk_multiplier(asset_symbol: str) -> Decimal:
    if asset_symbol == "PARLAY":
        return Decimal("0.75") 

    try:
        stock_qs = Stock.objects.filter(symbol=asset_symbol).first()
        if not stock_qs:
            return Decimal("1.00")
            
        active_markets = Market.objects.filter(
            stock=stock_qs, 
            is_active=True,
            expiry_date__gt=date.today()
        )
        if not active_markets.exists():
            return Decimal("1.00")

        # 1. Nudge Risk Calculation
        avg_nudge_agg = active_markets.aggregate(
            avg_o=Avg('net_effective_nudge_over'),
            avg_u=Avg('net_effective_nudge_under')
        )
        
        avg_nudge_over = avg_nudge_agg['avg_o'] or 0
        avg_nudge_under = avg_nudge_agg['avg_u'] or 0
        
        avg_nudge_risk = (abs(avg_nudge_over) + abs(avg_nudge_under)) / 2

        nudge_penalty_val = Decimal(str(avg_nudge_risk)) / Decimal("100.0")
        nudge_penalty = min(nudge_penalty_val, Decimal("0.10"))

        # 2. Implied Odds Balance Risk Calculation
        avg_implied_agg = active_markets.aggregate(
            avg_over=Avg('implied_odds_over'),
            avg_under=Avg('implied_odds_under')
        )
        
        prob_over = avg_implied_agg['avg_over'] or Decimal("0.50")
        prob_under = avg_implied_agg['avg_under'] or Decimal("0.50")

        max_deviation = max(abs(prob_over - Decimal("0.50")), abs(prob_under - Decimal("0.50")))
        
        prob_penalty_val = max_deviation / Decimal("2.0")
        prob_penalty = min(prob_penalty_val, Decimal("0.20")) 
        
        # 3. Combine and Set Floor
        base_multiplier = Decimal("1.00")
        final_multiplier = base_multiplier - nudge_penalty - prob_penalty
        
        return max(Decimal("0.50"), min(final_multiplier.quantize(Decimal("0.01"), ROUND_HALF_UP), Decimal("1.00")))

    except Exception:
        return Decimal("1.00")

def get_asset_crs_by_symbol(asset_symbol):
    asset_multiplier = calculate_asset_risk_multiplier(asset_symbol)
    return str(asset_multiplier)

def get_max_wager_percent_for_profile(profile_instance, base_market_max_payout=Decimal("500.00")):
    """Calculates the maximum allowed wager as a percentage of the user's current balance."""
    try:
        current_balance = profile_instance.user.wallet.balance
    except Exception:
        return "N/A"

    if current_balance is None or current_balance <= 0:
        return "0.00%" # Ensures a string is returned, avoiding None/Null

    REFERENCE_ODDS = Decimal("2.00") 
    
    max_wager_amount = profile_instance.max_wager_allowed(
        market_odds=REFERENCE_ODDS, 
        patron_risk_amount=base_market_max_payout
    )
    
    max_percent = (max_wager_amount / current_balance) * Decimal("100")
    
    if max_percent > Decimal("100.00"):
        max_percent = Decimal("100.00")
        
    return f"{max_percent.quantize(Decimal('0.01'), ROUND_HALF_UP)}%"


def get_user_bet_analytics_subquery(model, final_filter_kwargs, date_field):
    bet_sq = model.objects.filter(
        user_id=OuterRef(OuterRef('user_id')),
        **final_filter_kwargs
    ).select_related('market__stock').annotate(
        asset_symbol_key=F('market__stock__symbol'),
        parlay_key=Concat(
            Value('PARLAY'), 
            output_field=CharField()
        )
    ).order_by().values('user_id')

    if model == Bet:
        return bet_sq.values('asset_symbol_key').annotate(
            total_wagered_asset=Coalesce(Sum('amount_wagered'), Decimal("0.00"), output_field=DecimalField()),
            total_bets_asset=Coalesce(Count('id'), 0),
            most_recent_time=Max(date_field),
        ).values(
            'asset_symbol_key', 
            'total_wagered_asset', 
            'total_bets_asset', 
            'most_recent_time'
        ).order_by('-most_recent_time')
    
    if model == ParlayBet:
        return bet_sq.annotate(
            total_wagered_asset=Coalesce(Sum('amount_wagered'), Decimal("0.00"), output_field=DecimalField()),
            total_bets_asset=Coalesce(Count('id'), 0),
            most_recent_time=Max(date_field),
        ).values(
            'parlay_key', 
            'total_wagered_asset', 
            'total_bets_asset', 
            'most_recent_time'
        ).order_by('-most_recent_time')

# ---------- CORRECTED: user_analytics ----------

# def user_analytics(status_filter, user_query=None, date_from=None, date_to=None):
def user_analytics(status_filter, user_query=None, date_from=None, date_to=None, active_only=False):
    if status_filter not in ["settled", "pending"]:
        raise ValueError("Invalid status_filter. Must be 'settled' or 'pending'.")
        
    dt_from, dt_to = parse_date_range(date_from, date_to)
    
    if status_filter == "settled":
        status_kwargs = {"status__in": ["won", "lost", "void"]}
        date_field = "settled_at"
        output_ggr_key = "realized_ggr"
        output_payout_key = "total_payout"
    else:
        status_kwargs = {"status": "pending"}
        date_field = "created_at"
        output_ggr_key = "potential_ggr"
        output_payout_key = "potential_total_payout"

    date_kwargs = {}
    if dt_from:
        date_kwargs[f"{date_field}__gte"] = dt_from
    if dt_to:
        date_kwargs[f"{date_field}__lte"] = dt_to
    
    final_filter_kwargs = {**status_kwargs, **date_kwargs}
    prefetch_filter = Q(**final_filter_kwargs)

    users_qs = Profile.objects.select_related("user", "user__wallet", "user__kyc_profile")

    if user_query:
        users_qs = users_qs.filter(user__username__icontains=user_query)
    
    single_wager_sq = Bet.objects.filter(
        user=OuterRef('user_id'), **final_filter_kwargs
    ).values('user').annotate(total=Coalesce(Sum('amount_wagered'), Decimal("0.00"))).values('total')
    
    parlay_wager_sq = ParlayBet.objects.filter(
        user=OuterRef('user_id'), **final_filter_kwargs
    ).values('user').annotate(total=Coalesce(Sum('amount_wagered'), Decimal("0.00"))).values('total')
    
    users_qs = users_qs.annotate(
        total_single_wager=Subquery(single_wager_sq, output_field=DecimalField()),
        total_parlay_wager=Subquery(parlay_wager_sq, output_field=DecimalField()),
    )

    if status_filter == "settled":
        single_payout_sq = Bet.objects.filter(
            user=OuterRef('user_id'), **final_filter_kwargs
        ).values('user').annotate(total=Coalesce(Sum('payout_amount'), Decimal("0.00"))).values('total')
        
        parlay_payout_sq = ParlayBet.objects.filter(
            user=OuterRef('user_id'), **final_filter_kwargs
        ).values('user').annotate(total=Coalesce(Sum('payout_amount'), Decimal("0.00"))).values('total')

        users_qs = users_qs.annotate(
            total_single_payout=Subquery(single_payout_sq, output_field=DecimalField()),
            total_parlay_payout=Subquery(parlay_payout_sq, output_field=DecimalField()),
        )
    
    users_qs = users_qs.prefetch_related(
        Prefetch(
            'user__bets',
            queryset=Bet.objects.filter(prefetch_filter)
                               .select_related('market__stock')
                               .order_by(f'-{date_field}'),
            to_attr='prefetched_single_bets'
        ),
        Prefetch(
            'user__parlay_bets',
            queryset=ParlayBet.objects.filter(prefetch_filter)
                                     .prefetch_related(
                                         Prefetch(
                                             'legs', 
                                             queryset=Bet.objects.select_related('market__stock'),
                                             to_attr='prefetched_legs'
                                         )
                                     )
                                     .order_by(f'-{date_field}'),
            to_attr='prefetched_parlay_bets'
        ),
    )
    
    users_data = []

    for p in users_qs:
        user = p.user
        single_bets = user.prefetched_single_bets
        parlay_bets = user.prefetched_parlay_bets

        total_wager_single = _to_decimal(p.total_single_wager or Decimal("0.00"))
        total_wager_parlay = _to_decimal(p.total_parlay_wager or Decimal("0.00"))
        total_wager = (total_wager_single + total_wager_parlay).quantize(Decimal("0.01"), ROUND_HALF_UP)
        total_bets = len(single_bets) + len(parlay_bets)

        # Use profile max_stake to calculate percentage relative to current wager volume
        max_wager_percent = Decimal("0.00")
        if total_wager > 0:
            max_wager_percent = ((p.max_stake / total_wager) * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        ggr = Decimal("0.00")
        total_payout = Decimal("0.00")
        
        if status_filter == "settled":
            total_payout_single = _to_decimal(p.total_single_payout or Decimal("0.00"))
            total_payout_parlay = _to_decimal(p.total_parlay_payout or Decimal("0.00"))
            total_payout = (total_payout_single + total_payout_parlay).quantize(Decimal("0.01"), ROUND_HALF_UP)
            ggr = total_wager - total_payout
        elif status_filter == "pending":
            for bet in single_bets:
                total_payout += bet.get_potential_payout() or Decimal("0.00")
            for parlay in parlay_bets:
                total_payout += parlay.get_potential_payout() or Decimal("0.00")
            total_payout = total_payout.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ggr = total_wager - total_payout
            
        ggr = ggr.quantize(Decimal("0.01"), ROUND_HALF_UP)
        hold_pct = (ggr / total_wager * Decimal("100")).quantize(Decimal("0.01"), ROUND_HALF_UP) if total_wager > 0 else Decimal("0.00")

        balance = round_two_places(user.wallet.balance) if hasattr(user, 'wallet') and user.wallet and user.wallet.balance is not None else "N/A"
        kyc_status = user.kyc_profile.kyc_status if hasattr(user, 'kyc_profile') and user.kyc_profile else "N/A"

        # Asset group logic - changed to store list of all bets
        asset_groups = defaultdict(lambda: {
            "total_wagered_asset": Decimal("0.00"),
            "total_bets_asset": 0,
            "bets_list": []
        })
        
        for bet in single_bets:
            stock_symbol = bet.market.stock.symbol if bet.market and bet.market.stock else "UNKNOWN"
            asset_groups[stock_symbol]["total_wagered_asset"] += _to_decimal(bet.amount_wagered)
            asset_groups[stock_symbol]["total_bets_asset"] += 1
            asset_groups[stock_symbol]["bets_list"].append(bet)

        for bet in parlay_bets:
            stock_symbol = "PARLAY"
            asset_groups[stock_symbol]["total_wagered_asset"] += _to_decimal(bet.amount_wagered)
            asset_groups[stock_symbol]["total_bets_asset"] += 1
            asset_groups[stock_symbol]["bets_list"].append(bet)

        recent_bets_by_asset = []
        for symbol, data in asset_groups.items():
            formatted_bets = []
            all_symbols_in_group = set()
            
            for bet in data["bets_list"]:
                is_parlay = isinstance(bet, ParlayBet)
                bet_data, selection, stock_symbols = format_bet_data(bet, is_parlay, status_filter, date_field)
                formatted_bets.append(bet_data)
                all_symbols_in_group.update(stock_symbols)

            display_symbol = " | ".join(all_symbols_in_group) if symbol == "PARLAY" and all_symbols_in_group else symbol
            crs_by_asset = get_asset_crs_by_symbol("PARLAY" if symbol == "PARLAY" else symbol)

            recent_bets_by_asset.append({
                "asset_symbol": display_symbol,
                "max_percent_wager": f"{max_wager_percent}%",
                "crs_by_asset": crs_by_asset,
                "total_bets_asset": data["total_bets_asset"],
                "most_recent_bets": formatted_bets # contains all bets in the period
            })
        
        # Sort asset groups by the time of the most recent bet in that group
        recent_bets_by_asset.sort(key=lambda x: x["most_recent_bets"][0]["bet_time"] if x["most_recent_bets"] else "", reverse=True)
        users_data.append({
            "user_id": user.id,
            "username": user.username,
            "kyc_status": kyc_status,
            "email": user.email,
            "balance": balance,
            "crs_risk_score": p.crs_risk_score,
            "crs_risk_level": p.crs_risk_level,
            "total_handle": money_str(total_wager),
            output_payout_key: money_str(total_payout),
            output_ggr_key: money_str(ggr),
            "hold_percent": str(hold_pct),
            "total_bets": total_bets,
            "recent_bets_by_asset": recent_bets_by_asset,
        })

    users_sorted = sorted(users_data, key=lambda x: _to_decimal(x[output_ggr_key]), reverse=True)
    crs_distribution = list(users_qs.values("crs_risk_level").annotate(count=Count("id")).order_by("crs_risk_level"))

    return {
        "total_users": len(users_data),
        "status_filter": status_filter,
        "date_range": {"from": date_from, "to": date_to},
        "crs_distribution": crs_distribution,
        "users": users_sorted,
    }


def format_bet_data(bet, is_parlay, status_filter, date_field):
    stock_symbols = []
    wager = _to_decimal(bet.amount_wagered)

    if not is_parlay:
        market = bet.market
        stock_symbol = market.stock.symbol if market and market.stock else "UNKNOWN"
        stock_symbols.append(stock_symbol)
        
        try:
            odds_placement = Decimal(str(getattr(bet, 'decimal_odds', 1.00))).quantize(Decimal("0.01"), ROUND_HALF_UP)
        except:
            odds_placement = 'N/A'
        
        if market and market.stock:
            expiry = market.expiry_date.strftime("%Y-%m-%d") if market.expiry_date else "N/A"
            strike = f"${market.target_price}" if market.target_price is not None else ""
            outcome = getattr(market, "outcome_type", None) or getattr(bet, "chosen_outcome", '').capitalize()
            selection = f"{stock_symbol} {expiry} | {outcome} {strike}".strip()
        else:
            selection = "Market details unavailable"
        no_of_legs = None
    else:
        legs = bet.prefetched_legs if hasattr(bet, 'prefetched_legs') else list(bet.legs.all().select_related('market__stock'))
        no_of_legs = len(legs)
        selection_parts = []
        
        for leg in legs:
            stock_sym = leg.market.stock.symbol if leg.market and leg.market.stock else "UNKNOWN"
            stock_symbols.append(stock_sym)
            if leg.market:
                m = leg.market
                exp_date = m.expiry_date.strftime("%Y-%m-%d") if m.expiry_date else "Date N/A"
                outcome = getattr(leg, 'chosen_outcome', '').capitalize()
                selection_parts.append(f"{stock_sym} ({exp_date} {outcome})")
            else:
                selection_parts.append(f"Leg {leg.id} N/A")

        selection = " | ".join(selection_parts) if selection_parts else "Parlay legs unavailable"
        
        try:
            raw_odds = bet.get_combined_decimal_odds() if hasattr(bet, 'get_combined_decimal_odds') else 1.00
            odds_placement = Decimal(str(raw_odds)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        except:
            odds_placement = 'N/A'

    bet_data = {
        "bet_time": getattr(bet, date_field).strftime("%Y-%m-%d %H:%M:%S") if getattr(bet, date_field) else 'N/A',
        "bet_id": bet.id,
        "category": "parlay" if is_parlay else "single",
        "selection": selection,
        "wager": money_str(wager),
        "status": bet.status,
        "odds_at_placement": str(odds_placement), 
        "no_of_legs": no_of_legs,
    }

    if status_filter == 'settled':
        payout_val = _to_decimal(bet.payout_amount)
        bet_data.update({
            "payout": money_str(payout_val),
            "realized_ggr": money_str(wager - payout_val),
        })
    else:
        potential_payout_val = _to_decimal(bet.get_potential_payout() or 0)
        bet_data.update({
            "potential_payout": money_str(potential_payout_val),
            "potential_ggr": money_str(wager - potential_payout_val),
        })
        
    return bet_data, selection, stock_symbols
# def user_analytics(status_filter=None, user_query=None, date_from=None, date_to=None):
#     """
#     Patron analytics summary and detail for matched users, filtered by status ("settled" or "pending").

#     Returns:
#       - total_users, crs_distribution (counts per crs level),
#       - top_users and worst_users (by GGR/Potential GGR),
#       - users: list of patrons with totals and a truncated bet list (for drill-down).
#     Monetary values are strings with two decimals.
#     """
#     if status_filter not in ["settled", "pending"]:
#         raise ValueError("Invalid status_filter. Must be 'settled' or 'pending'.")
        
#     dt_from, dt_to = parse_date_range(date_from, date_to)
#     users_qs = Profile.objects.select_related("user", "user__wallet", "user__kyc_profile")

#     if user_query:
#         users_qs = users_qs.filter(user__username__icontains=user_query)

#     users_data = []
    
#     if status_filter == "settled":
#         status_kwargs = {"status__in": ["won", "lost", "void"]}
#         date_field = "settled_at"
#         output_ggr_key = "realized_ggr"
#         output_payout_key = "total_payout"
#     else: # "pending"
#         status_kwargs = {"status": "pending"}
#         date_field = "created_at"
#         output_ggr_key = "potential_ggr"
#         output_payout_key = "potential_total_payout"

#     for p in users_qs:
#         user = p.user

#         single_bets_qs = Bet.objects.filter(user=user, **status_kwargs)
#         parlay_qs = ParlayBet.objects.filter(user=user, **status_kwargs)

#         if dt_from:
#             single_bets_qs = single_bets_qs.filter(**{f"{date_field}__gte": dt_from})
#             parlay_qs = parlay_qs.filter(**{f"{date_field}__gte": dt_from})
#         if dt_to:
#             single_bets_qs = single_bets_qs.filter(**{f"{date_field}__lte": dt_to})
#             parlay_qs = parlay_qs.filter(**{f"{date_field}__lte": dt_to})

#         total_wager_single = single_bets_qs.aggregate(
#             total=Coalesce(Sum("amount_wagered"), Decimal("0.00"))
#         )["total"]
#         total_wager_parlay = parlay_qs.aggregate(
#             total=Coalesce(Sum("amount_wagered"), Decimal("0.00"))
#         )["total"]

#         total_wager = (total_wager_single + total_wager_parlay).quantize(Decimal("0.01"), ROUND_HALF_UP)
#         total_bets = single_bets_qs.count() + parlay_qs.count()
        
#         ggr = Decimal("0.00")
#         total_payout = Decimal("0.00")
        
#         if status_filter == "settled":
#             total_payout = single_bets_qs.aggregate(
#                 total=Coalesce(Sum("payout_amount"), Decimal("0.00"))
#             )["total"] + parlay_qs.aggregate(
#                 total=Coalesce(Sum("payout_amount"), Decimal("0.00"))
#             )["total"]
            
#             ggr = total_wager - total_payout
        
#         elif status_filter == "pending":
#             for bet in single_bets_qs:
#                 total_payout += bet.get_potential_payout() or Decimal("0.00")
#             for parlay in parlay_qs:
#                 total_payout += parlay.get_potential_payout() or Decimal("0.00")

#             total_payout = total_payout.quantize(Decimal("0.01"), ROUND_HALF_UP)
#             ggr = total_wager - total_payout
            
#         ggr = ggr.quantize(Decimal("0.01"), ROUND_HALF_UP)
        
#         hold_pct = Decimal("0.00")
#         if total_wager > 0:
#             hold_pct = (ggr / total_wager * Decimal("100")).quantize(Decimal("0.01"), ROUND_HALF_UP)

#         try:
#             balance = round_two_places(user.wallet.balance)
#         except Exception:
#             balance = None

#         try:
#             kyc_status = user.kyc_profile.kyc_status
#         except Exception:
#             kyc_status = None

#         combined_bets = sorted(
#             list(single_bets_qs) + list(parlay_qs), 
#             key=lambda x: getattr(x, date_field), 
#             reverse=True
#         )[:10]
#         recent_bets = []

#         for bet in combined_bets:
#             is_parlay = isinstance(bet, ParlayBet)
            
#             if hasattr(bet, 'market') and bet.market:
#                 stock_symbol = bet.market.stock.symbol if hasattr(bet.market, 'stock') and bet.market.stock else None
#                 expiry = bet.market.expiry_date.strftime("%Y-%m-%d") if bet.market.expiry_date else None
#                 strike = f"${bet.market.target_price}" if bet.market.target_price is not None else None
#                 outcome = getattr(bet.market, "outcome_type", None)
#                 parts = [p for p in [stock_symbol, expiry] if p]
#                 sel_right = " ".join([p for p in [outcome, strike] if p])
#                 selection = f"{' '.join(parts)} | {sel_right}" if parts else sel_right or None
#             else:
#                 selection = f"Parlay ({bet.legs.count()} legs)" if is_parlay and hasattr(bet, 'legs') else "N/A"

#             wager = _to_decimal(bet.amount_wagered)
#             bet_data = {
#                 "bet_time": getattr(bet, date_field).strftime("%Y-%m-%d %H:%M:%S"),
#                 "bet_id": bet.id,
#                 "category": "parlay" if is_parlay else "single",
#                 "selection": selection,
#                 "wager": money_str(wager),
#                 "status": bet.status,
#             }

#             if status_filter == 'settled':
#                 payout_val = _to_decimal(bet.payout_amount)
#                 ggr_val = (wager - payout_val).quantize(Decimal("0.01"), ROUND_HALF_UP)
#                 bet_data.update({
#                     "payout": money_str(payout_val),
#                     "realized_ggr": money_str(ggr_val),
#                 })
#             else: # pending
#                 potential_payout_val = _to_decimal(bet.get_potential_payout() or 0)
#                 potential_ggr_val = (wager - potential_payout_val).quantize(Decimal("0.01"), ROUND_HALF_UP)
#                 bet_data.update({
#                     "potential_payout": money_str(potential_payout_val),
#                     "potential_ggr": money_str(potential_ggr_val),
#                 })
            
#             recent_bets.append(bet_data)

#         user_summary = {
#             "user_id": user.id,
#             "username": user.username,
#             "kyc_status": kyc_status,
#             "email": user.email,
#             "balance": balance,
#             "crs_risk_score": p.crs_risk_score,
#             "crs_risk_level": p.crs_risk_level,
#             "total_handle": money_str(total_wager),
#             output_payout_key: money_str(total_payout),
#             output_ggr_key: money_str(ggr),
#             "hold_percent": str(hold_pct),
#             "total_bets": total_bets,
#             "recent_bets": recent_bets,
#         }
#         users_data.append(user_summary)

#     ggr_key = output_ggr_key
#     users_sorted = sorted(users_data, key=lambda x: _to_decimal(x[ggr_key]), reverse=True)

#     crs_distribution_qs = users_qs.values("crs_risk_level").annotate(count=Count("id")).order_by("crs_risk_level")
#     crs_distribution = list(crs_distribution_qs)

#     return {
#         "total_users": len(users_data),
#         "status_filter": status_filter,
#         "date_range": {"from": date_from, "to": date_to},
#         "crs_distribution": crs_distribution,
#         "users": users_data,
#     }



def get_top_users_by_ggr(start_date=None, end_date=None, status_filter="all", top_n=5, reverse=False, include_parlays=False):
    """
    Returns top or worst users based on combined GGR from both Bet and ParlayBet.
    The GGR calculation respects the provided status_filter (settled/pending).
    """

    bets_qs = Bet.objects.select_related("user")
    if start_date:
        bets_qs = bets_qs.filter(created_at__date__gte=start_date)
    if end_date:
        bets_qs = bets_qs.filter(created_at__date__lte=end_date)
    
    if status_filter == "settled":
        settled_statuses = ["won", "lost", "void"]
        bets_qs = bets_qs.filter(status__in=settled_statuses)
    elif status_filter == "pending":
        bets_qs = bets_qs.filter(status="pending")
    
    
    parlays_qs = ParlayBet.objects.select_related("user")
    if include_parlays:
        if start_date:
            parlays_qs = parlays_qs.filter(created_at__date__gte=start_date)
        if end_date:
            parlays_qs = parlays_qs.filter(created_at__date__lte=end_date)

        if status_filter == "settled":
            parlays_qs = parlays_qs.filter(status__in=settled_statuses)
        elif status_filter == "pending":
            parlays_qs = parlays_qs.filter(status="pending")


    if status_filter == "pending":
        
        combined = defaultdict(lambda: {"user_id": None, "username": "", "ggr": Decimal("0.00")})
        
        for bet in bets_qs.filter(is_parlay_leg=False):
            uid = bet.user_id
            combined[uid]["user_id"] = uid
            combined[uid]["username"] = bet.user.username
            
            wager = bet.amount_wagered or Decimal("0")
            potential_payout = bet.get_potential_payout()
            combined[uid]["ggr"] += wager - potential_payout

        if include_parlays:
            for parlay in parlays_qs:
                uid = parlay.user_id
                combined[uid]["user_id"] = uid
                combined[uid]["username"] = parlay.user.username
                
                wager = parlay.amount_wagered or Decimal("0")
                potential_payout = parlay.get_potential_payout()
                combined[uid]["ggr"] += wager - potential_payout

        combined_values = list(combined.values())
        
    else:
        
        bet_data = (
            bets_qs.values("user__id", "user__username")
            .annotate(
                total_wager=Coalesce(Sum("amount_wagered"), Value(0, output_field=DecimalField())),
                total_payout=Coalesce(Sum("payout_amount"), Value(0, output_field=DecimalField())),
            )
            .annotate(ggr=F("total_wager") - F("total_payout"))
        )

        if include_parlays:
            parlay_data = (
                parlays_qs.values("user__id", "user__username")
                .annotate(
                    total_wager=Coalesce(Sum("amount_wagered"), Value(0, output_field=DecimalField())),
                    total_payout=Coalesce(Sum("payout_amount"), Value(0, output_field=DecimalField())),
                )
                .annotate(ggr=F("total_wager") - F("total_payout"))
            )

            combined = defaultdict(lambda: {"user_id": None, "username": "", "ggr": Decimal("0.00")})
            for u in bet_data:
                uid = u["user__id"]
                combined[uid]["user_id"] = uid
                combined[uid]["username"] = u["user__username"]
                combined[uid]["ggr"] += u["ggr"]
            
            for u in parlay_data:
                uid = u["user__id"]
                combined[uid]["user_id"] = uid
                combined[uid]["username"] = u["user__username"]
                combined[uid]["ggr"] += u["ggr"]

            combined_values = list(combined.values())
        
        else:
            combined_values = bet_data

    if status_filter == "pending" or include_parlays:
        
        combined_values.sort(key=lambda x: x["ggr"], reverse=not reverse)
        ordered_results = combined_values[:top_n]
        
        return [
            {
                # FIX: Use 'user_id' key from the merged dictionary
                "user_id": u["user_id"],
                "username": u["username"],
                "ggr": round_two_places(u["ggr"]),
            }
            for u in ordered_results
        ]
    
    else:
        # This branch uses the QuerySet result where the key is 'user__id'
        ordered = combined_values.order_by("-ggr" if not reverse else "ggr")[:top_n]
        return [
            {
                "user_id": u["user__id"],
                "username": u["user__username"],
                "ggr": round_two_places(u["ggr"])
            }
            for u in ordered
        ]

def get_active_inactive_users():
    """Return count of active (30d bettors) and inactive bettors. Status-agnostic."""
    thirty_days_ago = date.today() - timedelta(days=30)

    all_bettor_ids = set(
        Bet.objects.values_list("user_id", flat=True)
    )

    active_ids = set(
        Bet.objects.filter(created_at__date__gte=thirty_days_ago)
        .values_list("user_id", flat=True)
        .distinct()
    )

    active_count = len(active_ids)
    total_users = len(all_bettor_ids)
    inactive_count = max(total_users - active_count, 0)

    return active_count, inactive_count, active_ids

def calculate_hold_percent(ggr, wager):
    if wager > 0:
        return str((ggr / wager * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return "0.00"

def overall_analytics(date_from=None, date_to=None, status_filter="all", active_only=False):
    today = timezone.now().date()

    # ---- Default date range: last 30 days ----
    if not date_from and not date_to:
        date_from = today - timezone.timedelta(days=30)
        date_to = today

    # ---- Parse dates ----
    if isinstance(date_from, str):
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
    if isinstance(date_to, str):
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

    date_from_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, time.max))

    # ---- Base QuerySets ----
    all_bets_qs = Bet.objects.select_related("user")
    all_parlay_qs = ParlayBet.objects.select_related("user")

    # ---- Optional Active Users Filtering ----
    active_users, inactive_users, active_ids = get_active_inactive_users()
    if active_only:
        # active_user_ids = [u.id for u in active_ids]
        all_bets_qs = all_bets_qs.filter(user__id__in=active_ids)
        all_parlay_qs = all_parlay_qs.filter(user__id__in=active_ids)

    # ---- Status-specific filtering ----
    if status_filter == "all":
        # Include all bets that either settled within range OR are still pending
        all_bets_qs = all_bets_qs.filter(
            Q(status="pending") | Q(settled_at__range=(date_from_dt, date_to_dt))
        )
        all_parlay_qs = all_parlay_qs.filter(
            Q(status="pending") | Q(settled_at__range=(date_from_dt, date_to_dt))
        )

    elif status_filter == "pending":
        # Bets still active (not settled yet)
        all_bets_qs = all_bets_qs.filter(
            status="pending",
            created_at__date__lte=date_to
        )
        all_parlay_qs = all_parlay_qs.filter(
            status="pending",
            created_at__date__lte=date_to
        )

    elif status_filter == "settled":
        # Bets that actually settled within the range
        settled_filter_statuses = ["won", "lost", "void"]
        all_bets_qs = all_bets_qs.filter(
            status__in=settled_filter_statuses,
            settled_at__range=(date_from_dt, date_to_dt)
        )
        all_parlay_qs = all_parlay_qs.filter(
            status__in=settled_filter_statuses,
            settled_at__range=(date_from_dt, date_to_dt)
        )

    # ---- Total bet count ----
    total_bets_count = all_bets_qs.count() + all_parlay_qs.count()

    result = {
        "date_range": {"from": date_from, "to": date_to},
        "status_filter": status_filter,
        "active_only": active_only,
        "last_updated": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_bets_count": total_bets_count,
    }

    # ---- Settled Metrics ----
    if status_filter in ["settled", "all"]:
        settled_filter_statuses = ["won", "lost", "void"]

        settled_bets_qs = all_bets_qs.filter(
            status__in=settled_filter_statuses,
            settled_at__range=(date_from_dt, date_to_dt)
        )
        settled_parlay_qs = all_parlay_qs.filter(
            status__in=settled_filter_statuses,
            settled_at__range=(date_from_dt, date_to_dt)
        )

        settled_bet_agg = settled_bets_qs.aggregate(
            wager=Coalesce(Sum("amount_wagered"), Decimal("0.00")),
            payout=Coalesce(Sum("payout_amount"), Decimal("0.00")),
        )
        settled_parlay_agg = settled_parlay_qs.aggregate(
            wager=Coalesce(Sum("amount_wagered"), Decimal("0.00")),
            payout=Coalesce(Sum("payout_amount"), Decimal("0.00")),
        )

        total_wager_settled = settled_bet_agg["wager"] + settled_parlay_agg["wager"]
        total_payout_settled = settled_bet_agg["payout"] + settled_parlay_agg["payout"]
        settled_ggr = total_wager_settled - total_payout_settled
        hold_pct_settled = calculate_hold_percent(settled_ggr, total_wager_settled)

        result.update({
            "settled_ggr": round_two_places(settled_ggr),
            "total_wager_settled": round_two_places(total_wager_settled),
            "total_payout_settled": round_two_places(total_payout_settled),
            "hold_percent_settled": hold_pct_settled,
        })

    # ---- Pending Metrics ----
    if status_filter in ["pending", "all"]:
        pending_bets_qs = all_bets_qs.filter(status="pending")
        pending_parlay_qs = all_parlay_qs.filter(status="pending")

        total_pending_wager = (
            pending_bets_qs.aggregate(total=Coalesce(Sum("amount_wagered"), Decimal("0.00")))["total"]
            + pending_parlay_qs.aggregate(total=Coalesce(Sum("amount_wagered"), Decimal("0.00")))["total"]
        )

        total_pending_payout = Decimal("0.00")
        for bet in pending_bets_qs:
            total_pending_payout += bet.get_potential_payout() or Decimal("0.00")
        for pb in pending_parlay_qs:
            total_pending_payout += pb.get_potential_payout() or Decimal("0.00")

        pending_ggr = total_pending_wager - total_pending_payout
        hold_pct_pending = calculate_hold_percent(pending_ggr, total_pending_wager)

        result.update({
            "total_wager_pending": round_two_places(total_pending_wager),
            "total_payout_pending": round_two_places(total_pending_payout),
            "potential_ggr": round_two_places(pending_ggr),
            "hold_percent_pending": hold_pct_pending,
        })

    # ---- User Metrics ----
    top_users = get_top_users_by_ggr(
        date_from, date_to, status_filter=status_filter, top_n=5, include_parlays=True
    )
    worst_users = get_top_users_by_ggr(
        date_from, date_to, status_filter=status_filter, top_n=5, reverse=True, include_parlays=True
    )

    result.update({
        "active_users": active_users,
        "inactive_users": inactive_users,
        "top_users": top_users,
        "worst_users": worst_users,
    })

    return result

# def overall_analytics(date_from=None, date_to=None, status_filter="all"):
#     """
#     High-level platform analytics (overlap-aware).

#     Includes:
#       - Bets created before and settled within range (realized)
#       - Bets created before and still open in range (exposure)
#     """

#     today = timezone.now().date()
#     settled_filter = ["won", "lost", "void"]

#     all_bets_qs = Bet.objects.select_related("user").all()
#     all_parlay_qs = ParlayBet.objects.select_related("user").all()

#     if not date_from and not date_to:
#         date_from = today - timezone.timedelta(days=30)
#         date_to = today

#     overlap_filter = Q()
#     if date_from and date_to:
#         overlap_filter = Q(created_at__date__lte=date_to) & (
#             Q(settled_at__isnull=True) | Q(settled_at__date__gte=date_from)
#         )
#     elif date_from:
#         overlap_filter = Q(created_at__date__gte=date_from)
#     elif date_to:
#         overlap_filter = Q(created_at__date__lte=date_to)

#     all_bets_qs = all_bets_qs.filter(overlap_filter)
#     all_parlay_qs = all_parlay_qs.filter(overlap_filter)

#     settled_ggr = Decimal("0.00")
#     total_settled_wager = Decimal("0.00")
#     total_settled_payout = Decimal("0.00")

#     if status_filter in ["settled", "all"]:
#         settled_bets_qs = all_bets_qs.filter(status__in=settled_filter)
#         if date_from:
#             settled_bets_qs = settled_bets_qs.filter(settled_at__date__gte=date_from)
#         if date_to:
#             settled_bets_qs = settled_bets_qs.filter(settled_at__date__lte=date_to)

#         settled_parlay_qs = all_parlay_qs.filter(status__in=settled_filter)
#         if date_from:
#             settled_parlay_qs = settled_parlay_qs.filter(settled_at__date__gte=date_from)
#         if date_to:
#             settled_parlay_qs = settled_parlay_qs.filter(settled_at__date__lte=date_to)

#         settled_bet_agg = settled_bets_qs.aggregate(
#             wager=Coalesce(Sum("amount_wagered"), Decimal("0.00")),
#             payout=Coalesce(Sum("payout_amount"), Decimal("0.00")),
#         )
#         settled_parlay_agg = settled_parlay_qs.aggregate(
#             wager=Coalesce(Sum("amount_wagered"), Decimal("0.00")),
#             payout=Coalesce(Sum("payout_amount"), Decimal("0.00")),
#         )

#         total_settled_wager = settled_bet_agg["wager"] + settled_parlay_agg["wager"]
#         total_settled_payout = settled_bet_agg["payout"] + settled_parlay_agg["payout"]
#         settled_ggr = total_settled_wager - total_settled_payout

#     total_pending_wager = Decimal("0.00")
#     total_pending_payout = Decimal("0.00")
#     pending_ggr = Decimal("0.00")
#     hold_pct_pending = Decimal("0.00")

#     if status_filter in ["pending", "all"]:
#         pending_bets_qs = all_bets_qs.filter(
#             status="pending", created_at__date__lte=(date_to or today)
#         )
#         pending_parlay_qs = all_parlay_qs.filter(
#             status="pending", created_at__date__lte=(date_to or today)
#         )

#         total_pending_wager = (
#             pending_bets_qs.aggregate(total=Coalesce(Sum("amount_wagered"), Decimal("0.00")))["total"]
#             + pending_parlay_qs.aggregate(total=Coalesce(Sum("amount_wagered"), Decimal("0.00")))["total"]
#         )

#         for bet in pending_bets_qs:
#             total_pending_payout += bet.get_potential_payout() or Decimal("0.00")
#         for pb in pending_parlay_qs:
#             total_pending_payout += pb.get_potential_payout() or Decimal("0.00")

#         pending_ggr = total_pending_wager - total_pending_payout

#         if total_pending_wager > 0:
#             hold_pct_pending = (pending_ggr / total_pending_wager * 100).quantize(
#                 Decimal("0.01"), rounding=ROUND_HALF_UP
#             )

#     active_users, inactive_users = get_active_inactive_users()
#     top_users = get_top_users_by_ggr(date_from, date_to, top_n=5, include_parlays=True)
#     worst_users = get_top_users_by_ggr(date_from, date_to, top_n=5, reverse=True, include_parlays=True)

#     return {
#         "date_range": {"from": date_from, "to": date_to or today},
#         "status_filter": status_filter,
#         "total_wager_pending": round_two_places(total_pending_wager),
#         "total_payout_pending": round_two_places(total_pending_payout),
#         "potential_ggr": round_two_places(pending_ggr),
#         "hold_percent_pending": str(hold_pct_pending),
#         "settled_ggr": round_two_places(settled_ggr),
#         "total_wager_settled": round_two_places(total_settled_wager),
#         "total_payout_settled": round_two_places(total_settled_payout),
#         "active_users": active_users,
#         "inactive_users": inactive_users,
#         "top_users": top_users,
#         "worst_users": worst_users,
#         "last_updated": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
#     }

def get_settlement_groups_v4(status_filter=None, search=None):

    """
    Groups bets by: (ticker | side/outcome | strike | expiry | status)
    Ensures group_title is always returned.
    Excludes bets where ticker/asset is missing.
    Adds 'hyperlink' field for frontend to expand/collapse bet details.
    """
    bets = (
        Bet.objects
        .select_related("user", "market__stock")
        .order_by("-settled_at", "-created_at")
    )

    # Filter by status
    if status_filter:
        bets = bets.filter(status=status_filter.lower())

    # Filter by search: ticker or expiry
    if search:
        bets = bets.filter(
            Q(market__stock__symbol__icontains=search) |
            Q(market__expiry_date__icontains=search)
        )

    grouped = defaultdict(lambda: {"group_title": "", "bets": [], "hyperlink": ""})

    for bet in bets:
        market = bet.market
        stock = market.stock if (market and market.stock) else None

        # Exclude bets with missing ticker/asset
        if not stock or not stock.symbol:
            continue

        ticker = stock.symbol
        strike = float(getattr(market, "target_price", 0) or 0)
        expiry_date = (
            market.expiry_date.strftime("%Y-%m-%d") if market and market.expiry_date else "-"
        )
        side = bet.chosen_outcome.capitalize() if bet.chosen_outcome else "-"
        status_val = (bet.status or "pending").lower()
        bet_type = "parlay" if getattr(bet, "is_parlay_leg", False) else "single"

        # Unique group key
        key = f"{ticker}_{side}_{strike}_{expiry_date}_{status_val}"

        # Human-readable group title
        group_title = f"{ticker} | {side} ${strike} | {expiry_date} | {status_val.capitalize()}"
        grouped[key]["group_title"] = group_title

        # Add hyperlink for frontend expansion
        # grouped[key]["hyperlink"] = f"/admin/settlements/group/{key}/"

        # Append individual bet
        grouped[key]["bets"].append({
            "bet_id": bet.id,
            "bet_type": bet_type,
            "username": getattr(bet.user, "username", "-"),
            "amount_wagered": float(bet.amount_wagered or 0),
            "payout_amount": float(bet.payout_amount or 0),
            "potential_payout": float(getattr(bet, "get_potential_payout", lambda: 0)()),
            "odds": {
                "american": getattr(bet, "odds_at_placement", "-"),
                "decimal": float(getattr(bet, "decimal_odds", 0) or 0),
                "fractional": getattr(bet, "fractional_odds", "-"),
            },
            "placed_at": bet.created_at.strftime("%Y-%m-%d %H:%M:%S") if bet.created_at else None,
            "settled_at": bet.settled_at.strftime("%Y-%m-%d %H:%M:%S") if bet.settled_at else None,
            "status": status_val,
            "ticker": ticker,
            "strike_price": strike,
            "expiry_date": expiry_date,
            "outcome": side,
        })

    # Convert grouped dict to list with totals
    final_groups = []
    for entry in grouped.values():
        bets_list = entry["bets"]
        total_handle = round(sum(b["amount_wagered"] for b in bets_list), 2)
        total_payout = round(sum(b["payout_amount"] for b in bets_list), 2)

        final_groups.append({
            "group_title": entry["group_title"],
            "total_bets": len(bets_list),
            "total_handle": total_handle,
            "total_payout": total_payout,
            "bets": bets_list,
        })

    # Sort: settled first (won/lost), then void, then pending
    status_order = {"won": 1, "lost": 1, "void": 2, "pending": 3}
    final_groups.sort(
        key=lambda g: status_order.get(
            g["bets"][0]["status"] if g["bets"] else "pending", 99
        )
    )

    return final_groups