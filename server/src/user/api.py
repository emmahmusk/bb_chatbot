import logging
import uuid
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status, permissions, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from twilio.rest import Client
from .models import KYCProfile, Profile, Wallet, Transaction
from .serializers import KYCProfileSerializer
from decimal import Decimal
from .serializers import (
    CombinedProfileSerializer,
    EmailVerificationSerializer,
    ProfileSerializer,
)
from django.utils.timezone import make_aware
from datetime import datetime
from rest_framework.pagination import PageNumberPagination

logger = logging.getLogger(__name__)


class SignupAPIView(APIView):
    def post(self, request):
        data = request.data

        if User.objects.filter(username=data.get("username")).exists():
            return Response({"error": "Username already exists"}, status=400)

        if User.objects.filter(email=data.get("email")).exists():
            return Response({"error": "Email already exists"}, status=400)
        try:
            user = User.objects.create(
                username=data.get("username"),
                email=data.get("email"),
                password=make_password(data.get("password")),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)
        # Optional: Log the user in for session-based features
        try:
            # Create profile with extended KYC fields
            profile = Profile.objects.create(
                user=user,
                phone=data.get("phone"),
                date_of_birth=data.get("date_of_birth"),
                current_address=data.get("current_address"),
                home_address=data.get("home_address"),
                city=data.get("city"),
                postal_code=data.get("postal_code"),
            )
            kyc_profile = KYCProfile.objects.create(user=user)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        # refresh = RefreshToken.for_user(user)

        return Response(
            {
                "profile": ProfileSerializer(profile).data,
                # "access": str(refresh.access_token),
                # "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        user = authenticate(
            username=request.data.get("username"),
            password=request.data.get("password"),
        )
        if not user:
            return Response({"error": "Invalid username or password"}, status=400)

        # Optional: Log the user in for session-based features
        login(request, user)

        # Ensure KYC and Wallet exist
        KYCProfile.objects.get_or_create(user=user)
        Wallet.objects.get_or_create(user=user)

        # Preload related objects to avoid null wallet balance
        user = (
            User.objects.select_related("profile", "wallet")
            .get(id=user.id)
        )

        # Create JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "profile": ProfileSerializer(user.profile).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=200,
        )


class RetrieveUpdateProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Retrieve both profile and KYC details."""
        serializer = CombinedProfileSerializer({
            "profile": request.user.profile,
            "kyc_profile": getattr(request.user, "kyc_profile", None)
        })
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Update both profile and KYC details in one request."""
        serializer = CombinedProfileSerializer(
            instance=request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmailSendVerifyOTP(APIView):
    permission_classes = [permissions.IsAuthenticated]
    """
    Handles sending and verifying OTP via email using Twilio Verify service.
    """

    @transaction.atomic
    def get(self, request):
        """
        Sends an OTP to the specified email.
        """
        email = request.GET.get("email")
        if not email:
            return JsonResponse(
                {"status": "error", "message": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = email.strip().lower()
        client = Client(settings.TWILIO_ACCOUNT_ID, settings.TWILIO_AUTH_TOKEN)
        try:
            verification = client.verify.v2.services(
                settings.TWILIO_SERVICE_ID
            ).verifications.create(
                channel_configuration={
                    "template_id": settings.SENDGRID_EMAIL_VERIFY_TEMPLATE_ID,
                    "from": settings.NO_REPLY,
                    "from_name": "BULLBEAR NO-REPLY",
                },
                to=email,
                channel="email",
            )
            return JsonResponse(
                {"code": "200", "status": verification.status, "message": "success"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": "An unexpected error occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    def post(self, request):
        """
        Verifies the OTP sent to the email.
        """
        otp = request.data.get("otp")
        email = request.data.get("email")
        if not otp or not email:
            return JsonResponse(
                {"status": "error", "message": "OTP and email are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = email.strip().lower()
        client = Client(settings.TWILIO_ACCOUNT_ID, settings.TWILIO_AUTH_TOKEN)
        try:
            verification_check = client.verify.v2.services(settings.TWILIO_SERVICE_IDs).verification_checks.create(to=email, code=otp)

            if verification_check.status != "approved":
                return JsonResponse(
                    {
                        "code": "500",
                        "status": f"{verification_check.status}",
                        "message": "OTP not approved.",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return JsonResponse(
                {"status": f"{verification_check.status}", "message": "success"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VerifyEmailAPIView(APIView):
    """
    Endpoint for a user to mark their email as verified.
    For now, it simply sets email_verified to True.
    In a robust system, this would involve a verification token/external proof.
    """

    permission_classes = [permissions.IsAuthenticated]  # User must be logged in

    def post(self, request, *args, **kwargs):
        """
        Handles the POST request to verify the user's email.
        """
        user = request.user

        # Ensure the user has a profile
        if not hasattr(user, "profile"):
            return Response(
                {"error": "User does not have a linked profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = user.profile

        if profile.email_verified:
            return Response(
                {"message": "Email is already verified."},
                status=status.HTTP_200_OK,  # Or 400 if you prefer to indicate no action
            )
        try:
            with transaction.atomic():
                profile.email_verified = True
                profile.save()
                logger.info(f"User {user.username}'s email marked as verified.")

            serializer = EmailVerificationSerializer(
                {
                    "message": "Email has been successfully verified.",
                    "email_verified": profile.email_verified,
                }
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"Error verifying email for user {user.username}: {e}", exc_info=True
            )
            return Response(
                {
                    "error": "An unexpected error occurred during email verification. Please try again."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class KYCFileUploadAPIView(APIView):
    """
    Upload or update KYC document and selfie image for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]  # enables file upload

    def patch(self, request, *args, **kwargs):
        """
        Partial update of KYCProfile for file uploads (id_document or selfie_image).
        """
        user = request.user
        kyc_profile, _ = KYCProfile.objects.get_or_create(user=user)

        serializer = KYCProfileSerializer(kyc_profile, data=request.data, partial=True, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "success", "kyc_profile": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WalletFundView(APIView):
    """
    Allows authenticated users (or admin) to fund a user's wallet.
    Logs the credit transaction and updates the wallet balance atomically.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        amount = request.data.get("amount")
        description = request.data.get("description", "Wallet funding")
        reference = request.data.get("reference")

        try:
            amount = Decimal(amount)
            if amount <= 0:
                return Response({"detail": "Amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST)
        wallet, _ = Wallet.objects.get_or_create(user=user)
        reference = f"TRX-FUND-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        wallet.balance = Decimal(wallet.balance) + amount
        wallet.save(update_fields=["balance", "updated_at"])
        transaction_entry = Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=Transaction.CREDIT,
            description=description,
            reference=reference,
        )

        return Response(
            {
                "message": "success",
                "new_balance": wallet.balance,
                "transaction": {
                    "id": transaction_entry.id,
                    "type": transaction_entry.transaction_type,
                    "amount": transaction_entry.amount,
                    "description": transaction_entry.description,
                    "reference": transaction_entry.reference,
                    "created_at": transaction_entry.created_at,
                },
            },
            status=status.HTTP_201_CREATED,
        )

class StandardResultsSetPagination(PageNumberPagination):
    """
    Reusable pagination class — you can use this for any list view.
    """
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class WalletTransactionHistoryView(APIView):
    """
    Returns paginated transaction history for the authenticated user's wallet.
    Supports optional date filtering via ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD.
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        user = request.user
        wallet = getattr(user, "wallet", None)
        if not wallet:
            return Response(
                {"detail": "Wallet not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        transactions_qs = wallet.transactions.all().order_by("-created_at")

        # --- 1️⃣ Optional date filtering ---
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        try:
            if start_date_str:
                start_date = make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"))
                transactions_qs = transactions_qs.filter(created_at__gte=start_date)
            if end_date_str:
                end_date = make_aware(datetime.strptime(end_date_str, "%Y-%m-%d"))
                transactions_qs = transactions_qs.filter(created_at__lte=end_date)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- 2️⃣ Paginate results ---
        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(transactions_qs, request)

        # --- 3️⃣ Serialize output ---
        transactions_data = [
            {
                "id": tx.id,
                "transaction_type": tx.transaction_type,
                "amount": tx.amount,
                "description": tx.description,
                "reference": tx.reference,
                "created_at": tx.created_at,
            }
            for tx in paginated_qs
        ]

        # --- 4️⃣ Return paginated response ---
        return paginator.get_paginated_response({
            "wallet_balance": wallet.balance,
            "transactions": transactions_data
        })


class WalletWithdrawView(APIView):
    """
    Allows an authenticated user to withdraw funds from their wallet.
    Performs validation, ensures sufficient balance, logs the transaction,
    and updates wallet atomically.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        amount = request.data.get("amount")
        description = request.data.get("description", "Wallet withdrawal")
        
        try:
            kyc_profile = user.kyc_profile
            if kyc_profile.kyc_status == "rejected":
                return Response(
                    {
                        "status": "error",
                        "message": "Your KYC has been rejected. You are not allowed to place bets.",
                        "kyc_status": kyc_profile.kyc_status,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        except KYCProfile.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": "KYC record not found. Please complete KYC verification before placing bets.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # --- 1️⃣ Validate amount ---
        try:
            amount = Decimal(amount)
            if amount <= 0:
                return Response({"detail": "Amount must be greater than zero."},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "Invalid amount format."},
                            status=status.HTTP_400_BAD_REQUEST)

        # --- 2️⃣ Get wallet ---
        wallet = getattr(user, "wallet", None)
        if not wallet:
            return Response({"detail": "Wallet not found."},
                            status=status.HTTP_404_NOT_FOUND)

        # --- 3️⃣ Check sufficient balance ---
        if wallet.balance < amount:
            return Response({"detail": "Insufficient wallet balance."},
                            status=status.HTTP_400_BAD_REQUEST)

        # --- 4️⃣ Deduct balance atomically ---
        wallet.balance = (Decimal(wallet.balance) - amount).quantize(Decimal("0.01"))
        wallet.save(update_fields=["balance", "updated_at"])
        reference = f"TRX-DEBIT-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        # --- 5️⃣ Log transaction ---
        transaction_entry = Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=Transaction.DEBIT,
            description=description,
            reference=reference
        )

        # --- 6️⃣ Response ---
        return Response({
            "message": "success",
            "new_balance": wallet.balance,
            "transaction": {
                "id": transaction_entry.id,
                "type": transaction_entry.transaction_type,
                "amount": transaction_entry.amount,
                "description": transaction_entry.description,
                "reference": transaction_entry.reference,
                "created_at": transaction_entry.created_at,
            }
        }, status=status.HTTP_201_CREATED)