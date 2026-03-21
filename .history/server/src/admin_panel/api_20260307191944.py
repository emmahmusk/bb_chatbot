from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.utils.timezone import now
import uuid
import hashlib
import json
import logging
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login
from betengine.models import Bet, Market
from betengine.serializers import BetSerializer
from mkt.alpha_vantage_utils import get_current_stock_price
from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from user.models import KYCProfile, Profile, Wallet, Transaction
from user.serializers import FullProfileSerializer, KYCFileReviewSerializer, ProfileSerializer, UserBetStatsSerializer
from .serializers import KYCReviewSerializer, AdminBetSerializer
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta, date
from rest_framework.pagination import PageNumberPagination
from user.models import PlatformSettings
from user.wallet_utils import get_or_create_wallet_with_starting_coins
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.utils import timezone

from . import analytics as utils
from .utils import (
    get_daily_volume,
    get_active_users_last_30_days,
    get_total_ggr,
    get_total_profits,
    get_liabilities_snapshot,
    get_pending_kyc_count,
    get_pending_bet_settlement_count,
    get_profits_vs_losses_last_6_months,
    get_user_bet_stats,
    get_win_loss_ratio_last_6_months,
    get_recent_bets,
    get_settlement_ratio_last_6_months,
)

User = get_user_model()

logger = logging.getLogger(__name__)

def update_user_crs(user_id, new_crs):
    """
    Update CRS risk score and auto-adjust max wager allowed.
    """
    try:
        profile = Profile.objects.get(user_id=user_id)
        profile.crs_risk_score = new_crs
        # Example dynamic rule
        profile.max_wager_allowed = max(100, 1000 * (new_crs / 20))
        profile.save()
        return {"success": True, "new_score": new_crs, "max_wager_allowed": profile.max_wager_allowed}
    except Profile.DoesNotExist:
        return {"success": False, "error": "User not found"}

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        user = authenticate(
            username=request.data.get("username"),
            password=request.data.get("password")
        )
        if not user:
            return Response({"error": "Invalid username or password"}, status=400)

        login(request, user)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "profile": ProfileSerializer(user.profile).data,
                "is_admin": user.profile.is_admin,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=200,
        )


class SignupAPIView(APIView):
    permission_classes = [AllowAny]  # Could restrict if needed

    def post(self, request):
        data = request.data

        if User.objects.filter(username=data.get("username")).exists():
            return Response({"error": "Username already exists"}, status=400)

        if User.objects.filter(email=data.get("email")).exists():
            return Response({"error": "Email already exists"}, status=400)

        # Only an authenticated admin can create another admin
        requested_admin_flag = bool(data.get("is_admin", False))
        is_admin = False
        if requested_admin_flag and request.user.is_authenticated:
            if hasattr(request.user, "profile") and request.user.profile.is_admin:
                is_admin = True

        try:
            user = User.objects.create(
                username=data.get("username"),
                email=data.get("email"),
                password=make_password(data.get("password")),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
            )

            profile = Profile.objects.create(
                user=user,
                is_admin=is_admin,
                phone=data.get("phone"),
                date_of_birth=data.get("date_of_birth"),
                current_address=data.get("current_address"),
                home_address=data.get("home_address"),
                city=data.get("city"),
                postal_code=data.get("postal_code"),
            )

            KYCProfile.objects.create(user=user)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

        return Response(
            {"profile": ProfileSerializer(profile).data},
            status=status.HTTP_201_CREATED,
        )

class KYCFileReviewListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all KYC profiles with file info for admin review."""
        kyc_profiles = KYCProfile.objects.select_related("user").all()
        serializer = KYCFileReviewSerializer(kyc_profiles, many=True)
        return Response(serializer.data)

    def put(self, request, pk=None):
        """
        Update a specific KYC profile.
        Expected payload example:
        {
            "kyc_status": "approved",
            "reviewer_comment": "Document is valid"
        }
        """
        kyc_id = request.data.get("id") or pk
        if not kyc_id:
            return Response({"error": "KYC profile ID is required"}, status=400)

        try:
            kyc_profile = KYCProfile.objects.get(id=kyc_id)
        except KYCProfile.DoesNotExist:
            return Response({"error": "KYC profile not found"}, status=404)

        serializer = KYCFileReviewSerializer(kyc_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": f"KYC profile {kyc_id} updated successfully",
                "data": serializer.data
            })
        return Response(serializer.errors, status=400)

class AdminUserListView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        # if not hasattr(request.user, "profile") or not request.user.profile.is_admin:
        #     return Response({"error": "You do not have permission to view this resource."}, status=status.HTTP_403_FORBIDDEN)
        profiles = Profile.objects.select_related("user").order_by("user__id")
        serialized_profiles = FullProfileSerializer(profiles, many=True, context={"request": request}).data

        return Response({
            "count": len(serialized_profiles),
            "profiles": serialized_profiles
        }, status=status.HTTP_200_OK)



class AdminBetsFeedPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminBetFeedView(APIView):
    """
    Paginated feed for admin bet settlements dashboard.
    Supports search, filter by status, and standard pagination.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        status_filter = request.query_params.get("status", "").strip()

        # Base Queryset
        bets = (
            Bet.objects.select_related("user", "market", "market__stock")
            .filter(market__isnull=False, market__stock__isnull=False)
            .order_by("-created_at")
        )
        if status_filter == "settled":
            bets = bets.filter(status__in=["won", "lost", "void"])

        if status_filter:
            bets = bets.filter(status__iexact=status_filter)

        if search:
            bets = bets.filter(
                models.Q(user__username__icontains=search)
                | models.Q(market__stock__symbol__icontains=search)
                | models.Q(id__icontains=search)
            )

        # Pagination
        paginator = AdminBetsFeedPagination()
        paginated_bets = paginator.paginate_queryset(bets, request)

        # Serialize paginated results
        serializer = AdminBetSerializer(paginated_bets, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminKYCViewSet(viewsets.ModelViewSet):
    queryset = KYCProfile.objects.select_related("user", "user__profile")
    serializer_class = KYCFileReviewSerializer
    permission_classes = [IsAdminUser]
    lookup_field = "user_id"
    lookup_url_kwarg = "pk"

    def get_serializer_class(self):
        if self.action in ["review_kyc"]:
            return KYCFileReviewSerializer
        return KYCFileReviewSerializer

    def filter_queryset(self, queryset):
        """
        Allow filtering by ?status=pending/approved/rejected.
        """
        status_filter = self.request.query_params.get("status")
        if status_filter in ["pending", "approved", "rejected"]:
            queryset = queryset.filter(kyc_status=status_filter)
        return queryset

    @action(detail=True, methods=["patch"], url_path="review")
    def review_kyc(self, request, pk=None):
        """Approve or reject a KYC profile."""
        kyc_profile = self.get_object()
        serializer = KYCFileReviewSerializer(kyc_profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=200)


# 2. SETTLE A BET
class AdminSettleBetView(APIView):
    permission_classes = [IsAuthenticated]
    """
    safe window to settle bets after market expiry date
    ~4:30 PM ET (market close + buffer) to 9:00 AM ET the next day.
    """
    def post(self, request, bet_id):
        try:
            bet = Bet.objects.get(pk=bet_id)
        except Bet.DoesNotExist:
            return Response({"error": "Bet not found"}, status=status.HTTP_404_NOT_FOUND)

        market = bet.market
        if not market:
            return Response({"error": "Market not found for this bet."}, status=400)

        today = now().date()
        if today < market.expiry_date:
            return Response(
                {"error": "Market has not expired yet. Cannot settle bet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ Check if admin wants to override
        override_outcome = request.data.get("override_outcome", None)  # "won" | "lost" | "void" | None
        if override_outcome:
            if override_outcome not in ["won", "lost", "void"]:
                return Response(
                    {"error": "Invalid override_outcome. Must be 'won', 'lost', or 'void'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            bet_outcome = override_outcome
            override_used = True
            final_price = None  # not applicable
        else:
            # Normal auto-settlement
            final_price = get_current_stock_price(
                market.stock.symbol,
                api_key=settings.ALPHA_VANTAGE_API_KEY
            )
            if final_price is None or final_price == 0:
                return Response({"error": "Unable to fetch final stock price."}, status=400)

            bet_outcome = "lost"

            if bet.chosen_outcome == "over":
                if final_price > market.target_price:
                    bet_outcome = "won"
                elif final_price == market.target_price:
                    bet_outcome = "void"
            elif bet.chosen_outcome == "under":
                if final_price < market.target_price:
                    bet_outcome = "won"
                elif final_price == market.target_price:
                    bet_outcome = "void"

            override_used = False

        # Apply settlement
        bet.status = bet_outcome
        bet.settled_at = now()
        bet.override_used = override_used

        if bet_outcome == "won":
            bet.payout_amount = bet.get_potential_payout()
        elif bet_outcome == "lost":
            bet.payout_amount = Decimal("0.00")
        elif bet_outcome == "void":
            bet.payout_amount = bet.amount_wagered

        bet.save()

        return Response({
            "message": f"Bet {bet_id} settled as {bet_outcome}.",
            "override_used": override_used,
            "final_price": str(final_price) if final_price else None,
            "bet": BetSerializer(bet).data
        }, status=status.HTTP_200_OK)

class AdminUserListAPIView(APIView):
    """
    Returns combined user data (username, balance, CRS, GGR, bet count, KYC status)
    using analytics logic from get_user_bet_stats().
    """
    authentication_classes = [] 
    permission_classes = [AllowAny]
    def get(self, request):
        user_stats = get_user_bet_stats()
        serializer = UserBetStatsSerializer(user_stats, many=True)
        return Response(serializer.data)


class AdminAnalyticsAPIView(APIView):
    """
    Returns all analytics data for the admin dashboard in a single API call.
    Allows filtering with query parameters.
    """
    permission_classes = [IsAuthenticated]  # optionally add IsAdminUser

    def get(self, request, *args, **kwargs):
        # Filters from query params
        period = request.query_params.get("period", "6m")  # default 6 months
        limit = int(request.query_params.get("limit", 5))

        # Period mapping
        today = date.today()
        if period == "30d":
            start_date = today - timedelta(days=30)
        elif period == "ytd":
            start_date = date(today.year, 1, 1)
        else:  # default 6 months
            start_date = today - timedelta(days=180)

        # Core data
        data = {
            "daily_volume": get_daily_volume(start_date),
            "active_users": get_active_users_last_30_days(),
            "total_profits": get_total_profits(month_to_date=(period == "30d")),
            "pending_kyc_count": get_pending_kyc_count(),
            "pending_bet_settlement_count": get_pending_bet_settlement_count(),
            "profits_vs_losses": get_profits_vs_losses_last_6_months(),
            "win_loss_ratio": get_win_loss_ratio_last_6_months(),
            "recent_bets": BetSerializer(get_recent_bets(limit=limit), many=True).data,
            "settlement_ratio": get_settlement_ratio_last_6_months(),
            "liabilities_snapshot": list(get_liabilities_snapshot(limit=limit)),
        }

        return Response(data)

class TotalGGRAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        GET /admin/ggr-total/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
        If no dates are provided, returns GGR from inception to today.
        """
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        active_users_only = request.query_params.get("active_users", "false") == "true"

        try:
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

        ggr_data = get_total_ggr(start_date, end_date, active_users_only)
        return Response({
            "total_ggr": ggr_data["ggr"],
            "total_payout": ggr_data["total_payout"],
            "total_wager": ggr_data["total_wager"],
            "total_users": ggr_data["users"],
            "currency": "USD",
            "start_date": start_date,
            "end_date": end_date
        })

class AdminFundUserWalletAPIView(APIView):
    """
    Admin-only endpoint to fund any user's wallet.
    Logs the credit transaction and updates the wallet atomically.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user_id = request.data.get("user_id")
        amount = request.data.get("amount")
        description = request.data.get("description", "Admin wallet funding")

        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            amount = Decimal(amount)
            if amount <= 0:
                return Response({"detail": "Amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST)

        wallet, _ = get_or_create_wallet_with_starting_coins(user=user)
        reference = f"TRX-ADMINFUND-{user.id}-{now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

        # Update balance
        wallet.balance = Decimal(wallet.balance) + amount
        wallet.save(update_fields=["balance", "updated_at"])

        # Log transaction
        transaction_entry = Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=Transaction.CREDIT,
            description=description,
            reference=reference,
        )

        return Response(
            {
                "message": f"Successfully funded {user.username}'s wallet",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
                "new_balance": str(wallet.balance),
                "transaction": {
                    "id": transaction_entry.id,
                    "type": transaction_entry.transaction_type,
                    "amount": str(transaction_entry.amount),
                    "description": transaction_entry.description,
                    "reference": transaction_entry.reference,
                    "created_at": transaction_entry.created_at,
                },
            },
            status=status.HTTP_201_CREATED,

        )


## CHETHAN NEW START

class AnalyticsDashboardAPIViewNew(APIView):
    """
    Incremental rebuild of admin analytics dashboard.

    - Path: /admin_panel/analytics/dashboard-new/
    - Same response shape as old AnalyticsDashboardAPIView:
        {
          "overall": {...},
          "market_analytics": {...},
          "bets_feed": {...},
          "meta": {...}
        }

    For now:
      - overall         → uses existing overall_analytics
      - market_analytics → uses existing market_analytics
      - bets_feed       → uses new bets_feed_v2

    Error behaviour:
      - If any section fails, that section will be:
            { "error": "<message>" }
      - meta will include:
            "errors": { "<section>": "<message>", ... },
            "has_errors": true/false
      So you can see exactly which block exploded on live.
    """

    permission_classes = [AllowAny]  # change to IsAdminUser if needed

    def get(self, request, *args, **kwargs):
        # ---- Raw query params from FE ----
        raw_date_from = request.query_params.get("date_from") or None
        raw_date_to = request.query_params.get("date_to") or None
        stock = request.query_params.get("stock")
        user_q = request.query_params.get("user")
        status_q = request.query_params.get("status") or "settled"
        search = request.query_params.get("search")

        active_only_param = request.query_params.get("active_only", "false").lower()
        active_only = active_only_param in ["true", "1", "yes"]

        # For incremental testing:
        #   /dashboard-new/?only=bets_feed
        #   /dashboard-new/?only=overall
        #   /dashboard-new/?only=market_analytics
        section_filter = request.query_params.get("only")

        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 25))
        except ValueError:
            page, page_size = 1, 25

        # ---- Normalize date range ----
        date_from, date_to = utils.normalize_date_inputs(raw_date_from, raw_date_to)

        response_data = {}

        # ---- Define subtasks (we can parallelize later if needed) ----
        def run_overall():
            return utils.overall_analytics_v2(
                date_from=date_from,
                date_to=date_to,
                status_filter=status_q,
                active_only=active_only,
            )

        def run_market():
            # market_analytics expects only 'settled' or 'pending'
            market_status = "pending" if status_q.lower() == "pending" else "settled"
            return utils.market_analytics_v2(
                stock_query=stock,
                date_from=date_from,
                date_to=date_to,
                status_filter=market_status,
            )

        def run_bets():
            # NEW: use bets_feed_v2 here
            return utils.bets_feed_v2(
                page=page,
                page_size=page_size,
                date_from=date_from,
                date_to=date_to,
                user=user_q,
                stock=stock,
                status=status_q,
                search=search,
            )

        analytics_tasks = {}
        if section_filter in (None, "overall"):
            analytics_tasks["overall"] = run_overall
        if section_filter in (None, "market_analytics"):
            analytics_tasks["market_analytics"] = run_market
        if section_filter in (None, "bets_feed"):
            analytics_tasks["bets_feed"] = run_bets

        # ---- Run tasks (sequential for now) ----
        errors: dict[str, str] = {}

        for name, func in analytics_tasks.items():
            try:
                response_data[name] = func()
            except Exception as e:
                # log full stack trace on server
                logger.exception("Error in %s computation: %s", name, e)
                # short, explicit error string in response
                msg = f"Failed to load {name.replace('_', ' ')}: {e}"
                response_data[name] = {"error": msg}
                errors[name] = msg

        # Ensure all keys exist so FE never crashes
        response_data.setdefault("overall", {})
        response_data.setdefault("market_analytics", {})
        response_data.setdefault("bets_feed", {})

        response_data["meta"] = {
            "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            "active_only": active_only,
            "cached": False,
            "date_from": date_from,
            "date_to": date_to,
            "errors": errors,              # section -> message
            "has_errors": bool(errors),    # quick flag
        }

        return Response(response_data, status=status.HTTP_200_OK)



## CHETHAN NEW END


class AnalyticsDashboardAPIView(APIView):
    """
    Consolidated analytics payload for the admin dashboard.
    Returns:
      - overall (Summary PnL Overview)
      - market_analytics (By stock)
      - user_summary (Patron-level)
      - bets_feed (Full bet stream)
    Now supports:
      - ?active_only=true
    Includes:
      - caching
      - parallel execution for sub-analytics
      - fault tolerance for partial failures
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        # ---- Query Params ----
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        stock = request.query_params.get("stock")
        user_q = request.query_params.get("user")
        status_q = request.query_params.get("status")
        search = request.query_params.get("search")

        # Active-only toggle
        active_only_param = request.query_params.get("active_only", "false").lower()
        active_only = active_only_param in ["true", "1", "yes"]

        # Pagination params
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 25))
        except ValueError:
            page, page_size = 1, 25

        # ---- Build cache key ----
        query_data = {
            "date_from": date_from,
            "date_to": date_to,
            "stock": stock,
            "user": user_q,
            "status": status_q,
            "search": search,
            "page": page,
            "page_size": page_size,
            "active_only": active_only,
        }
        cache_key = f"analytics_dashboard:{hashlib.md5(json.dumps(query_data, sort_keys=True).encode()).hexdigest()}"

        # ---- Check main dashboard cache ----
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response, status=status.HTTP_200_OK)

        # ---- Run analytics in parallel ----
        response_data = {}

        def run_overall():
            sub_key = f"overall_cache:{hashlib.md5(json.dumps(query_data, sort_keys=True).encode()).hexdigest()}"
            cached = cache.get(sub_key)
            if cached:
                return cached
            data = utils.overall_analytics(
                date_from=date_from,
                date_to=date_to,
                status_filter=status_q,
                active_only=active_only,
            )
            cache.set(sub_key, data, timeout=60)  # short-lived subcache
            return data

        def run_market():
            sub_key = f"market_cache:{hashlib.md5(json.dumps(query_data, sort_keys=True).encode()).hexdigest()}"
            cached = cache.get(sub_key)
            if cached:
                return cached
            data = utils.market_analytics(
                stock_query=stock,
                date_from=date_from,
                date_to=date_to,
                status_filter=status_q,
            )
            cache.set(sub_key, data, timeout=60)
            return data

        # def run_user():
        #     return utils.user_analytics(
        #         user_query=user_q,
        #         date_from=date_from,
        #         date_to=date_to,
        #         status_filter=status_q
        #     )

        def run_bets():
            return utils.bets_feed(
                page=page,
                page_size=page_size,
                date_from=date_from,
                date_to=date_to,
                user=user_q,
                stock=stock,
                status=status_q,
                search=search,
            )

        analytics_tasks = {
            "overall": run_overall,
            "market_analytics": run_market,
            "bets_feed": run_bets,
        }

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(func): name for name, func in analytics_tasks.items()}

            for future in as_completed(futures):
                name = futures[future]
                try:
                    response_data[name] = future.result()
                except Exception as e:
                    logger.exception("Error in %s computation: %s", name, e)
                    response_data[name] = {"error": f"Failed to load {name.replace('_', ' ')}"}

        # ---- Cache complete response ----
        try:
            cache.set(cache_key, response_data, timeout=300)
        except Exception as e:
            logger.warning("Failed to cache analytics response: %s", e)

        response_data["meta"] = {
            "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            "active_only": active_only,
            "cached": False,
        }

        return Response(response_data, status=status.HTTP_200_OK)


# class AnalyticsDashboardAPIView(APIView):
#     """
#     Consolidated analytics payload for the admin dashboard.
#     Returns:
#       - overall (Summary PnL Overview)
#       - user_summary (Patron analytics)
#       - bets_feed (Full bets feed)
#     Includes caching and fault tolerance for partial failures.
#     """
#     permission_classes = [AllowAny]

#     def get(self, request, *args, **kwargs):
#         # ---- Query Params ----
#         date_from = request.query_params.get("date_from") or None
#         date_to = request.query_params.get("date_to") or None
#         stock = request.query_params.get("stock")
#         user_q = request.query_params.get("user")
#         status_q = request.query_params.get("status")
#         search = request.query_params.get("search")

#         try:
#             page = int(request.query_params.get("page", 1))
#             page_size = int(request.query_params.get("page_size", 25))
#         except ValueError:
#             page, page_size = 1, 25

#         # ---- Build cache key ----
#         query_data = {
#             "date_from": date_from,
#             "date_to": date_to,
#             "stock": stock,
#             "user": user_q,
#             "status": status_q,
#             "search": search,
#             "page": page,
#             "page_size": page_size,
#         }
#         cache_key = f"analytics_dashboard:{hashlib.md5(json.dumps(query_data, sort_keys=True).encode()).hexdigest()}"

#         # ---- Check cache ----
#         cached_response = cache.get(cache_key)
#         if cached_response:
#             return Response(cached_response, status=status.HTTP_200_OK)

#         # ---- Compute analytics safely ----
#         response_data = {}

#         try:
#             response_data["overall"] = utils.overall_analytics(
#                 date_from=date_from,
#                 date_to=date_to,
#                 status_filter=status_q,
#             )
#         except Exception as e:
#             logger.exception("Error computing overall analytics: %s", e)
#             response_data["overall"] = {"error": "Failed to load overall analytics"}

#         try:
#             response_data["market_analytics"] = utils.market_analytics(
#                 stock_query=stock,
#                 date_from=date_from,
#                 date_to=date_to,
#                 status_filter=status_q,
#             )
#         except Exception as e:
#             logger.exception("Error computing market analytics: %s", e)
#             response_data["market_analytics"] = {"error": "Failed to load market analytics"}

#         try:
#             response_data["user_summary"] = utils.user_analytics(
#                 user_query=user_q,
#                 date_from=date_from,
#                 date_to=date_to,
#                 status_filter=status_q
#             )
#         except Exception as e:
#             logger.exception("Error computing user analytics: %s", e)
#             response_data["user_summary"] = {"error": "Failed to load user summary"}

#         try:
#             response_data["bets_feed"] = utils.bets_feed(
#                 page=page,
#                 page_size=page_size,
#                 date_from=date_from,
#                 date_to=date_to,
#                 user=user_q,
#                 stock=stock,
#                 status=status_q,
#                 search=search,
#             )
#         except Exception as e:
#             logger.exception("Error fetching bets feed: %s", e)
#             response_data["bets_feed"] = {"error": "Failed to load bets feed"}

#         # ---- Cache only successful responses ----
#         try:
#             cache.set(cache_key, response_data, timeout=300)
#         except Exception as e:
#             logger.warning("Failed to cache analytics response: %s", e)

#         return Response(response_data, status=status.HTTP_200_OK)

class AnalyticsUserDashboardAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        user_q = request.query_params.get("user")

        # Default status to pending (prevents ValueError)
        status_q = (request.query_params.get("status") or "pending").lower()

        active_only_param = request.query_params.get("active_only", "false").lower()
        active_only = active_only_param in ["true", "1", "yes"]

        query_data = {
            "date_from": date_from,
            "date_to": date_to,
            "user": user_q,
            "status": status_q,
            "active_only": active_only,
        }
        cache_key = f"user_analytics:{hashlib.md5(json.dumps(query_data, sort_keys=True).encode()).hexdigest()}"

        cached_response = cache.get(cache_key)
        if cached_response:
            cached_response["meta"] = {
                "cached": True,
                "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                "active_only": active_only,
            }
            return Response(cached_response, status=status.HTTP_200_OK)

        try:
            user_summary = utils.user_analytics(
                user_query=user_q,
                date_from=date_from,
                date_to=date_to,
                status_filter=status_q,
                active_only=active_only,
            )
        except Exception as e:
            logger.exception("Error computing user analytics: %s", e)
            user_summary = {"error": "Failed to load user summary"}

        response_data = {
            "user_summary": user_summary,
            "meta": {
                "cached": False,
                "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                "active_only": active_only,
            },
        }

        # Cache only success
        try:
            if not (isinstance(user_summary, dict) and user_summary.get("error")):
                cache.set(cache_key, response_data, timeout=120)
        except Exception as e:
            logger.warning("Failed to cache user analytics response: %s", e)

        return Response(response_data, status=status.HTTP_200_OK)



# class AnalyticsUserDashboardAPIView(APIView):
#     """
#     Consolidated analytics payload for the user-level dashboard.
#     Returns:
#       - user_summary (Patron analytics)
#     Supports:
#       - ?active_only=true
#       - caching and fault tolerance
#     """
#     permission_classes = [AllowAny]

#     def get(self, request, *args, **kwargs):
#         # ---- Query Params ----
#         date_from = request.query_params.get("date_from") or None
#         date_to = request.query_params.get("date_to") or None
#         user_q = request.query_params.get("user")
#         status_q = request.query_params.get("status")

#         # ---- Active-only filter ----
#         active_only_param = request.query_params.get("active_only", "false").lower()
#         active_only = active_only_param in ["true", "1", "yes"]

#         # ---- Build cache key ----
#         query_data = {
#             "date_from": date_from,
#             "date_to": date_to,
#             "user": user_q,
#             "status": status_q,
#             "active_only": active_only,
#         }
#         cache_key = f"user_analytics:{hashlib.md5(json.dumps(query_data, sort_keys=True).encode()).hexdigest()}"

#         # ---- Check cache ----
#         cached_response = cache.get(cache_key)
#         if cached_response:
#             cached_response["meta"] = {
#                 "cached": True,
#                 "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 "active_only": active_only,
#             }
#             return Response(cached_response, status=status.HTTP_200_OK)

#         # ---- Compute analytics safely ----
#         try:
#             user_summary = utils.user_analytics(
#                 user_query=user_q,
#                 date_from=date_from,
#                 date_to=date_to,
#                 status_filter=status_q,
#                 active_only=active_only,  # <== new param forwarded
#             )
#         except Exception as e:
#             logger.exception("Error computing user analytics: %s", e)
#             user_summary = {"error": "Failed to load user summary"}

#         # ---- Prepare response ----
#         response_data = {
#             "user_summary": user_summary,
#             "meta": {
#                 "cached": False,
#                 "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 "active_only": active_only,
#             },
#         }

#         # ---- Cache response (short lifespan for freshness) ----
#         try:
#             cache.set(cache_key, response_data, timeout=120)  # cache for 2 minutes
#         except Exception as e:
#             logger.warning("Failed to cache user analytics response: %s", e)

#         return Response(response_data, status=status.HTTP_200_OK)


class UpdatePlatformSettingsView(APIView):
    """
    Allows partial update of PlatformSettings.
    Only fields provided in the request will be updated.
    """

    permission_classes = [AllowAny]  # ⚠️ Strongly consider IsAdminUser in production

    def get(self, request):
        settings_obj = PlatformSettings.get_instance()
        return Response(
            {
                "base_exposure_limit": str(settings_obj.base_exposure_limit),
                "max_profit": str(settings_obj.max_profit),
                "max_crs": str(settings_obj.max_crs),
                "minimum_stake": str(settings_obj.minimum_stake),
                "max_risk_tolerance": str(settings_obj.max_risk_tolerance),
                "starting_coin_balance": str(settings_obj.starting_coin_balance),
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        """
        Partial update — only updates fields present in request.
        """
        settings_obj = PlatformSettings.get_instance()

        allowed_fields = {
            "base_exposure_limit",
            "max_profit",
            "max_crs",
            "minimum_stake",
            "max_risk_tolerance",
            "starting_coin_balance",
        }

        updated_fields = []

        try:
            for field in allowed_fields:
                if field in request.data:
                    value = request.data.get(field)

                    if value is None or value == "":
                        continue  # Skip empty values

                    decimal_value = Decimal(str(value))

                    if decimal_value < 0:
                        return Response(
                            {"success": False, "error": f"{field} cannot be negative."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    setattr(settings_obj, field, decimal_value)
                    updated_fields.append(field)

        except (ValueError, TypeError, InvalidOperation):
            return Response(
                {"success": False, "error": "All values must be valid decimal numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not updated_fields:
            return Response(
                {"success": False, "error": "No valid fields provided for update."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        settings_obj.save(update_fields=updated_fields)

        return Response(
            {
                "success": True,
                "updated_fields": updated_fields,
                "data": {
                    "base_exposure_limit": str(settings_obj.base_exposure_limit),
                    "max_profit": str(settings_obj.max_profit),
                    "max_crs": str(settings_obj.max_crs),
                    "minimum_stake": str(settings_obj.minimum_stake),
                    "max_risk_tolerance": str(settings_obj.max_risk_tolerance),
                    "starting_coin_balance": str(settings_obj.starting_coin_balance),
                },
            },
            status=status.HTTP_200_OK,
        )
    # Optional: keep POST for backward compatibility
    def post(self, request):
        return self.patch(request)

class DeleteExpiringMarketsView(APIView):
    """
    DELETE /markets/delete-expiring/
    Deletes all Market records with expiry_date <= today + 7 days.
    """
    permission_classes = [IsAuthenticated]  # ✅ Only admins can delete

    def delete(self, request, *args, **kwargs):
        today = now().date()
        cutoff_date = today + timedelta(days=7)

        markets_to_delete = Market.objects.filter(expiry_date__lte=cutoff_date)
        count = markets_to_delete.count()

        if count == 0:
            return Response(
                {"message": "No markets found that expire within 7 days."},
                status=status.HTTP_200_OK
            )

        markets_to_delete.delete()

        return Response(
            {"message": f"Successfully deleted {count} markets expiring on or before {cutoff_date}."},
            status=status.HTTP_200_OK
        )
  
class UpdateUserCRSView(APIView):
    """
    Admin endpoint to update a user's CRS risk score directly.
    POST payload: {
        "user_id": 123,
        "new_crs": "15.00"
    }
    """
    permission_classes = [AllowAny]

    def get(self, request):
        user_id = request.query_params.get("user_id", None)
        if not user_id:
            return Response(
                {"success": False, "error": "Profile not found for the given user_id."},
                status=status.HTTP_404_NOT_FOUND,
            )
        user = User.objects.get(id=user_id)
        profile = Profile.objects.get(user=user)
        return Response(
            {
                "success": True,
                "data": {
                    "user_id": user_id,
                    "usernme": profile.user.username,
                    "crs_risk_score": str(profile.crs_risk_score)
                },
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        user_id = request.data.get("user_id")
        new_crs = request.data.get("new_crs")

        if not user_id or not new_crs:
            return Response(
                {"success": False, "error": "Both user_id and new_crs are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_crs = Decimal(new_crs)
            if new_crs <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            return Response(
                {"success": False, "error": "new_crs must be a positive decimal number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = Profile.objects.get(user_id=user_id)
        except Profile.DoesNotExist:
            return Response(
                {"success": False, "error": "Profile not found for the given user_id."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update the CRS directly
        profile.crs_risk_score = new_crs
        profile.save()
        # profile.update_crs_risk()  # Ensure risk level is updated as well

        return Response(
            {
                "success": True,
                "message": f"User CRS updated to {new_crs}.",
                "data": {
                    "user_id": user_id,
                    "crs_risk_score": str(profile.crs_risk_score)
                },
            },
            status=status.HTTP_200_OK,
        )
    

class AdminMarketOverrideAPIView(APIView):
    """
    Allows admin to manually reactivate a suspended market side.
    """

    permission_classes = [AllowAny]

    def post(self, request, market_id):
        """
        POST /admin/markets/{market_id}/override/
        Optional body:
        {
            "over": true,
            "under": true
        }
        If no body provided, both sides are reactivated.
        """

        try:
            with transaction.atomic():
                market = Market.objects.select_for_update().get(id=market_id)

                override_over = request.data.get("over", True)
                override_under = request.data.get("under", True)

                updated_fields = []

                if override_over:
                    market.is_suspended_over = False
                    updated_fields.append("is_suspended_over")

                if override_under:
                    market.is_suspended_under = False
                    updated_fields.append("is_suspended_under")

                if market.requires_admin_override:
                    market.requires_admin_override = False
                    updated_fields.append("requires_admin_override")

                if updated_fields:
                    market.save(update_fields=updated_fields)

            return Response(
                {
                    "success": True,
                    "message": "Market override successful.",
                    "data": {
                        "market_id": market.id,
                        "is_suspended_over": market.is_suspended_over,
                        "is_suspended_under": market.is_suspended_under,
                        "requires_admin_override": market.requires_admin_override,
                    }
                },
                status=status.HTTP_200_OK,
            )

        except Market.DoesNotExist:
            return Response(
                {"success": False, "error": "Market not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Admin override error: {e}", exc_info=True)
            return Response(
                {"success": False, "error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )