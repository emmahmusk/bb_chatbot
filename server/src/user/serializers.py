from .models import KYCProfile, Profile, Wallet, CompetitionMember

# Serializer for CompetitionMember to expose competition_coin_balance and related fields
class CompetitionMemberSerializer(serializers.ModelSerializer):
    competition_coin_balance = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    competition_id = serializers.IntegerField(source="competition.id", read_only=True)
    competition_name = serializers.CharField(source="competition.name", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    joined_at = serializers.DateTimeField(read_only=True)
    final_rank = serializers.IntegerField(read_only=True)
    final_score = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_disqualified = serializers.BooleanField(read_only=True)

    class Meta:
        model = CompetitionMember
        fields = [
            "competition_id",
            "competition_name",
            "user_id",
            "username",
            "competition_coin_balance",
            "joined_at",
            "final_rank",
            "final_score",
            "is_disqualified",
        ]
from django.contrib.auth.models import User

from rest_framework import serializers

from betengine.models import Bet
from betengine.serializers import MarketSerializer

from .models import KYCProfile, Profile, Wallet

from decimal import Decimal

class PasswordResetOTPRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset OTP email.
    """
    email = serializers.EmailField(required=True)

class VerifyEmailOTPRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset OTP email.
    """
    email = serializers.EmailField(required=True)

# New serializer for verifying OTP and setting new password
class PasswordResetOTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying a password reset OTP and setting a new password.
    """
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6, help_text="The 6-digit OTP received via email.")
    new_password = serializers.CharField(required=True, min_length=8, write_only=True) # write_only hides it from response

    def validate_new_password(self, value):
        # Add stronger password validation rules here if needed
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        # Example: require a digit, uppercase, lowercase, special character
        # if not any(char.isdigit() for char in value):
        #     raise serializers.ValidationError("Password must contain at least one digit.")
        # if not any(char.isupper() for char in value):
        #     raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        return value

class VerifyEmailOTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying a password reset OTP and setting a new password.
    """
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6, help_text="The 6-digit OTP received via email.")

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]


class UserKPIsSerializer(serializers.Serializer):
    """
    Serializer to display aggregated KPIs for a specific user.
    """

    username = serializers.CharField(read_only=True)
    total_amount_wagered = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    total_net_pnl = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    crs_score = serializers.IntegerField(
        source="profile.crs_risk_score", read_only=True
    )
    crs_risk_level = serializers.CharField(
        source="profile.crs_risk_level", read_only=True
    )
    max_wager_allowed = serializers.DecimalField(
        source="profile.max_wager_allowed",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    email_verified = serializers.BooleanField(
        source="profile.email_verified", read_only=True
    )

    # You can add more profile details if needed
    date_of_birth = serializers.DateField(
        source="profile.date_of_birth", read_only=True
    )
    phone = serializers.CharField(source="profile.phone", read_only=True)


# class ProfileSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Profile
#         fields = ["id", "user", "email_verified"]

class ProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    phone_number = serializers.CharField(source="phone", allow_blank=True, allow_null=True)
    physical_address = serializers.CharField(source="current_address", allow_blank=True, allow_null=True)
    wallet_balance = serializers.SerializerMethodField()
    wallet_coin_balance = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id",
            "user_id",
            "username",
            "user",
            "email_verified",
            "full_name",
            "date_of_birth",
            "email",
            "phone_number",
            "physical_address",
            "home_address",
            "source_of_funds",
            "betting_preference",
            "crs_risk_level",
            "tax_residency_country",
            "wallet_balance",
            "wallet_coin_balance",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_wallet_balance(self, obj):
        """
        Safely return the user's wallet balance.
        Defaults to 0.00 if wallet does not exist.
        """
        try:
            return str(obj.user.wallet.balance.quantize(Decimal("0.00")))
        except Exception:
            return "0.00"

    def get_wallet_coin_balance(self, obj):
        try:
            return str(obj.user.wallet.coin_balance.quantize(Decimal("0.00")))
        except Exception:
            return "0.00"
class EmailVerificationSerializer(serializers.Serializer):
    """
    A simple serializer for the email verification endpoint.
    It doesn't take input, but provides a consistent output
    """

    message = serializers.CharField(read_only=True)
    email_verified = serializers.BooleanField(read_only=True)


class GlobalRiskSettingsSerializer(serializers.Serializer):
    """
    Serializer for handling global patron and company risk amounts.
    """
    patron_risk = serializers.FloatField(required=True, min_value=0.0)
    company_risk = serializers.FloatField(required=True, min_value=0.0)

class MarketRuleSerializer(serializers.Serializer):
    """
    Serializer for handling market-specific override rules.
    """
    id = serializers.CharField(read_only=True) # Firestore document ID
    ticker = serializers.CharField(required=True, max_length=10)
    patron_risk = serializers.FloatField(required=True, min_value=0.0)
    company_risk = serializers.FloatField(required=True, min_value=0.0)


class BetSerializer(serializers.ModelSerializer):
    market_details = serializers.SerializerMethodField()

    class Meta:
        model = Bet
        fields = [
            "id",
            "market",
            "market_details",
            "amount_wagered",
            "odds_at_placement",
            "chosen_outcome",
            "status",
            "payout_amount",
            "is_parlay_leg",
            "parlay_bet",
            "created_at",
            "settled_at",
        ]
        read_only_fields = fields

    def get_market_details(self, obj):
        """
        Returns real market details OR placeholder info if market was deleted.
        """

        # If market exists normally
        if obj.market and not isinstance(obj.market, dict) and hasattr(obj.market, "id"):
            return MarketSerializer(obj.market).data

class KYCProfileSerializer(serializers.ModelSerializer):
    id_document = serializers.FileField(use_url=True)
    selfie_image = serializers.ImageField(use_url=True)

    class Meta:
        model = KYCProfile
        fields = "__all__"

class UserBetStatsSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    profile_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    crs = serializers.IntegerField()
    crs_level = serializers.CharField(required=False, allow_blank=True)
    max_wager_allowed = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    ggr = serializers.DecimalField(max_digits=12, decimal_places=2)
    bet_count = serializers.IntegerField()
    kyc_status = serializers.CharField(allow_null=True)

class FullProfileSerializer(serializers.ModelSerializer):
    kyc_profile = KYCProfileSerializer(source="user.kyc_profile", read_only=True)

    class Meta:
        model = Profile
        fields = "__all__"  # All Profile fields plus kyc_profile
        extra_fields = ["kyc_profile"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["profile_id"] = instance.id
        data["user_id"] = instance.user.id
        data["username"] = instance.user.username
        kyc_profile = getattr(instance.user, "kyc_profile", None)
        data["kyc_profile"] = KYCProfileSerializer(
            kyc_profile, context=self.context
        ).data if kyc_profile else None
        return data


class CombinedProfileSerializer(serializers.Serializer):
    profile = ProfileSerializer()
    kyc_profile = KYCProfileSerializer()

    def update(self, instance, validated_data):
        # instance here will be the `request.user`
        profile_data = validated_data.get("profile", {})
        kyc_data = validated_data.get("kyc_profile", {})

        # Update Profile
        profile = instance.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        # Update KYCProfile
        kyc_profile, _ = KYCProfile.objects.get_or_create(user=instance)
        for attr, value in kyc_data.items():
            setattr(kyc_profile, attr, value)
        kyc_profile.save()

        return instance


class KYCFileReviewSerializer(serializers.ModelSerializer):
    raw_user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_id = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    document_name = serializers.SerializerMethodField()
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = KYCProfile
        fields = [
            "raw_user_id",
            "user_id",
            "full_name",       # ✅ Now included in fields
            "username",
            "email",
            "document_name",
            "document_url",
            "selfie_image",
            "id_document_type",
            "id_verified",
            "kyc_status",
            "reviewer_comment",
            "submitted_at",
            "reviewed_at"
        ]

    def get_user_id(self, obj):
        return f"U-{obj.user.id:05d}"

    def get_full_name(self, obj):
        first = obj.user.first_name or ""
        last = obj.user.last_name or ""
        return f"{first} {last}".strip()

    def get_document_name(self, obj):
        return obj.id_document.name.split("/")[-1] if obj.id_document else None

    def get_document_url(self, obj):
        return obj.id_document.url if obj.id_document else None



class KYCReviewUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCProfile
        fields = ["kyc_status", "reviewer_comment"]

