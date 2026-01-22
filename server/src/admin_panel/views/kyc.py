# admin_panel/views/kyc.py
import logging


from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework.decorators import action

from rest_framework import status, viewsets, generics
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_panel.permissions import IsAdmin
from admin_panel.serializers import (
    CRSRiskScoreSerializer,
    KYCReviewSerializer,
    KYCSubmitSerializer,
)
from admin_panel.services.logger import log_admin_action
from user.serializers import FullProfileSerializer
from user.models import KYCProfile, Profile

# User = get_user_model()

logger = logging.getLogger(__name__)

class ApproveKYCView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        profile = get_object_or_404(KYCProfile, user=user)

        serializer = KYCReviewSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(reviewed_at=now(), kyc_status="approved")
            user.profile.is_verified = True
            user.profile.save()
            return Response({"message": "KYC approved"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RejectKYCView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, user_id):
        kyc = get_object_or_404(KYCProfile, user_id=user_id)
        kyc.kyc_status = "rejected"
        kyc.reviewer_comment = request.data.get("comment", "")
        kyc.reviewed_at = now()
        kyc.save()
        log_admin_action(request.user, "KYC_REJECT", "pending", "rejected")
        return Response({"message": "KYC rejected"})


class SubmitKYCView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = KYCProfile.objects.get(user=request.user)
            serializer = KYCSubmitSerializer(profile, data=request.data, partial=True)
        except KYCProfile.DoesNotExist:
            serializer = KYCSubmitSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({"message": "KYC submitted successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KYCListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = KYCProfile.objects.select_related("user").filter(kyc_status="pending")
    serializer_class = KYCSubmitSerializer



class AdminKYCViewSet(viewsets.ModelViewSet):
    queryset = KYCProfile.objects.select_related("user", "user__profile")
    serializer_class = FullProfileSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action in ["review_kyc"]:
            return KYCReviewSerializer
        return FullProfileSerializer

    @action(detail=True, methods=["patch"], url_path="review")
    def review_kyc(self, request, pk=None):
        """Approve or reject a KYC profile."""
        kyc_profile = self.get_object()
        serializer = KYCReviewSerializer(kyc_profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": f"KYC status updated to {serializer.data['kyc_status']}"})

class KYCDetailView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        action = request.data.get("action")
        if action == "approve":
            return ApproveKYCView().post(request, user_id)
        elif action == "reject":
            return RejectKYCView().post(request, user_id)
        return Response({"error": "Invalid action"}, status=400)


class ManualKYCTriggerView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user_profile = get_object_or_404(Profile, user=user)

        manual_kyc_flag = request.data.get("manual_kyc_required")
        if manual_kyc_flag is None:
            return Response({"error": "manual_kyc_required field is required"}, status=400)

        user_profile.manual_kyc_required = manual_kyc_flag
        user_profile.save()
        return Response({"message": f"Manual KYC flag set to {manual_kyc_flag}"})


class CRSRiskScoreView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        return Response({
            "user_id": user.id,
            "crs_risk_score": user.crs_risk_score,
            "crs_risk_level": user.crs_risk_level,
        })

    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        reason = request.data.get("reason", "Manual override via admin")

        serializer = CRSRiskScoreSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            user.update_crs_risk(changed_by=request.user, reason=reason)
            return Response({"message": "CRS risk score updated with audit trail"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CRSRiskAuditLogView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        logs = user.crs_audits.order_by("-timestamp").values(
            "previous_score", "new_score",
            "previous_level", "new_level",
            "changed_by__email", "timestamp", "reason"
        )
        return Response({"audit_logs": list(logs)})
