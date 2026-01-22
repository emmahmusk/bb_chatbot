# user_app/views.py

import logging
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Sum, When  # For aggregations

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User

from rest_framework_simplejwt.authentication import JWTAuthentication

from admin_panel.utils import get_user_bet_stats

from .models import Profile

# Assuming Bet is in market_data.models
from .serializers import (BetSerializer, PasswordResetOTPRequestSerializer, PasswordResetOTPVerifySerializer, UserBetStatsSerializer, UserKPIsSerializer, VerifyEmailOTPRequestSerializer, VerifyEmailOTPVerifySerializer)
from betengine.models import Bet
from .superbase_utils import send_password_reset_otp_email, verify_otp_and_update_email_verified, verify_otp_and_update_password

logger = logging.getLogger(__name__)

# --- Other user-related API views (like VerifyEmailAPIView) would be here ---
# ...


# NEW: User KPIs Overview API View
class UserKPIsOverviewAPIView(generics.RetrieveAPIView):
    """
    Endpoint to retrieve key performance indicators (KPIs) for the authenticated user.
    Includes total wagered, PnL, CRS score, max wager allowed, and email verification status.
    """

    serializer_class = UserKPIsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Returns the current authenticated user's data with calculated KPIs.
        """
        user = self.request.user

        # Ensure user has a profile
        if not hasattr(user, "profile"):
            raise status.HTTP_404_NOT_FOUND(
                "User profile not found."
            )  # Or handle differently

        # Calculate Total Amount Wagered
        total_wagered_agg = Bet.objects.filter(user=user).aggregate(
            total_wagered=Sum("amount_wagered", output_field=DecimalField())
        )
        total_amount_wagered = total_wagered_agg["total_wagered"] or Decimal("0.00")

        # Calculate User PnL
        # PnL = (sum of payout_amount for won bets) - (sum of amount_wagered for all settled bets)
        user_pnl_agg = Bet.objects.filter(
            user=user,
            status__in=["won", "lost", "void"],  # Only settled bets affect PnL
        ).aggregate(
            total_net_pnl=Sum(
                Case(
                    When(status="won", then=F("payout_amount") - F("amount_wagered")),
                    When(status="lost", then=-F("amount_wagered")),
                    When(
                        status="void", then=0
                    ),  # Voided bets usually imply wager was returned or not deducted
                    default=0,
                    output_field=DecimalField(),
                )
            )
        )
        total_net_pnl = user_pnl_agg["total_net_pnl"] or Decimal("0.00")

        # Attach calculated values to the user object for serialization
        user.total_amount_wagered = total_amount_wagered
        user.total_net_pnl = total_net_pnl
        # crs_risk_score, crs_risk_level, max_wager_allowed are properties on user.profile

        return user


# NEW: User Bet History API View
class UserBetHistoryAPIView(generics.ListAPIView):
    """
    Endpoint to retrieve the detailed bet history for the authenticated user.
    Bets with deleted markets (market_id is NULL) are excluded.
    """

    serializer_class = BetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        return (
            Bet.objects.filter(user=user, market__isnull=False)  # <-- KEY FIX
            .select_related("user", "market__stock")
            .order_by("-created_at")
        )
# class UserBetHistoryAPIView(generics.ListAPIView):
#     """
#     Endpoint to retrieve the detailed bet history for the authenticated user.
#     """

#     serializer_class = BetSerializer  # Reusing the detailed BetSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         """
#         Returns all bets placed by the authenticated user, ordered by creation date.
#         """
#         user = self.request.user
#         # Optimize query by selecting related user, market, and stock data
#         return (
#             Bet.objects.filter(user=user)
#             .select_related("user", "market__stock")
#             .order_by("-created_at")
#         )

class PasswordResetOTPRequestView(APIView):
    permission_classes = [permissions.AllowAny] # Allow unauthenticated users to request OTP

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'success': False, 'message': 'User with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

        result = send_password_reset_otp_email(email)

        if result['success']:
            # Always return a generic success message for security, even if email doesn't exist
            return Response(
                {'message': 'If an account with that email exists, an OTP has been sent.'},
                status=status.HTTP_200_OK
            )
        else:
            # Log the actual error internally but return generic message to frontend
            print(f"Internal error sending OTP for email {email}: {result['error']}")
            return Response(
                {'message': 'If an account with that email exists, an OTP has been sent.'},
                status=status.HTTP_200_OK
            )


class PasswordResetOTPVerifyView(APIView):
    permission_classes = [permissions.AllowAny] # Allow unauthenticated users to verify OTP

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        new_password = serializer.validated_data['new_password']

        result = verify_otp_and_update_password(email, otp_code, new_password)

        if result['success']:
            return Response(
                {'message': result['message']},
                status=status.HTTP_200_OK
            )
        else:
            # Return specific error from Supabase for verification failures
            return Response(
                {'error': result['error']},
                status=status.HTTP_400_BAD_REQUEST # 400 for incorrect OTP/email
            )

class VerifyEmailRequestOTP(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = VerifyEmailOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'success': False, 'message': 'User with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

        result = send_password_reset_otp_email(email)

        if result['success']:
            # Always return a generic success message for security, even if email doesn't exist
            return Response(
                {'message': 'If an account with that email exists, an OTP has been sent.'},
                status=status.HTTP_200_OK
            )
        else:
            # Log the actual error internally but return generic message to frontend
            print(f"Internal error sending OTP for email {email}: {result['error']}")
            return Response(
                {'message': f'Internal error sending OTP for email {email}: {result['error']}'},
                status=status.HTTP_400_BAD_REQUEST
            )

class VerifyEmailOTPVerify(APIView):
    permission_classes = [permissions.AllowAny] # Allow unauthenticated users to verify OTP

    def post(self, request, *args, **kwargs):
        serializer = VerifyEmailOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']

        result = verify_otp_and_update_email_verified(email, otp_code)

        if result['success']:
            return Response(
                {'message': result['message']},
                status=status.HTTP_200_OK
            )
        else:
            # Return specific error from Supabase for verification failures
            return Response(
                {'error': result['error']},
                status=status.HTTP_400_BAD_REQUEST # 400 for incorrect OTP/email
            )
        
class BettingPreferenceView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        preference = request.data.get("preference")
        valid_options = ['decimal', 'american', 'fraction']

        if preference not in valid_options:
            return Response(
                {"error": "Invalid preference. Choose from decimal, american, or fraction."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        profile, created = Profile.objects.get_or_create(user=user)
        profile.betting_preference = preference
        profile.save()

        return Response({"message": f"Betting preference set to {preference}"})


class UserBetsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        stats = get_user_bet_stats(user=request.user)
        serializer = UserBetStatsSerializer(stats, many=True)
        return Response(serializer.data)