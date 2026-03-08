from decimal import Decimal

from django.contrib.auth import get_user_model

from rest_framework import serializers

from admin_panel.models import BetOverrideLog, CRSModificationLog
from betengine.models import Bet, Market
from betengine.models import Stock
from user.models import KYCProfile, Profile, PlatformSettings  # adjust import

User = get_user_model()

# class BetSerializer(serializers.ModelSerializer):
#     user = serializers.StringRelatedField()
#     stock = serializers.StringRelatedField()

#     class Meta:
#         model = Bet
#         fields = [
#             "id", "user", "stock", "direction", "target_price",
#             "stake", "status", "placed_at", "settled_at", "result_price", "payout"
#         ]


class KYCSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCProfile
        fields = "__all__"
        # exclude = ["kyc_status", "reviewed_by", "reviewed_at"]
        # read_only_fields = ["user"]


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_verified", "balance", "date_joined"]



class AdminBetSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Bet
        fields = [
            "id",
            "user",
            "stock_symbol",
            "bet_type",
            "stake",
            "odds",
            "target_price",
            "result_price",
            "placed_at",
            "status",
            "resolved",
        ]


class CRSRiskScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["crs_risk_score", "crs_risk_level"]

class KYCReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCProfile
        fields = ["kyc_status", "reviewer_comment"]

    def update(self, instance, validated_data):
        instance.kyc_status = validated_data.get("kyc_status", instance.kyc_status)
        instance.reviewer_comment = validated_data.get(
            "reviewer_comment", instance.reviewer_comment
        )
        from django.utils import timezone
        instance.reviewed_at = timezone.now()
        instance.save()
        return instance



class AdminBetSerializer(serializers.ModelSerializer):
    """
    Serializer for admin bets feed with computed GGR and neatly wrapped odds formats,
    including key Profile metrics like crs_risk_score and max_stake.

    Dynamically returns parlay_id instead of id if the bet is part of a parlay.
    """
    bet_id = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    ticker = serializers.SerializerMethodField()
    strike_price = serializers.SerializerMethodField()
    expiry_date = serializers.SerializerMethodField()
    potential_payout = serializers.SerializerMethodField()
    ggr = serializers.SerializerMethodField()
    odds = serializers.SerializerMethodField()
    stake = serializers.DecimalField(source="amount_wagered", max_digits=10, decimal_places=2)

    # Profile-related fields
    crs_risk_score = serializers.SerializerMethodField()
    crs_risk_level = serializers.SerializerMethodField()
    max_wager_pct = serializers.SerializerMethodField()
    allowable_profit = serializers.SerializerMethodField()

    class Meta:
        model = Bet
        fields = [
            "bet_id",  # dynamically resolved id or parlay_id
            "username",
            "ticker",
            "odds",
            "stake",
            "potential_payout",
            "ggr",
            "status",
            "chosen_outcome",
            "strike_price",
            "expiry_date",
            "settled_at",
            "created_at",
            # --- Profile Data ---
            "crs_risk_score",
            "crs_risk_level",
            "max_wager_pct",
            "allowable_profit",
        ]

    # ---------- COMPUTED FIELDS ----------
    def get_bet_id(self, obj):
        """
        Returns parlay_id if the bet is a parlay leg, otherwise its own id.
        """
        # Handle both field naming possibilities gracefully
        if getattr(obj, "is_parlay_leg", False) and getattr(obj, "parlay_bet", None):
            return obj.parlay_bet.id
        return obj.id

    def get_username(self, obj):
        return f"@{obj.user.username}" if obj.user else None

    def get_ticker(self, obj):
        return obj.market.stock.symbol if obj.market and obj.market.stock else None

    def get_strike_price(self, obj):
        return float(obj.market.target_price) if obj.market and obj.market.target_price else None

    def get_expiry_date(self, obj):
        return obj.market.expiry_date if obj.market else None

    def get_potential_payout(self, obj):
        return float(obj.get_potential_payout())

    def get_ggr(self, obj):
        """
        GGR = payout_amount - amount_wagered
        """
        wager = obj.amount_wagered or Decimal("0")
        potential_payout = obj.get_potential_payout() or Decimal("0")
        ggr_value = potential_payout - wager
        return float(ggr_value)

    def get_odds(self, obj):
        """
        Wraps all odds formats inside a single JSON object.
        """
        if not obj.odds_at_placement:
            return None

        odds_data = obj.odds_at_placement
        return {
            "decimal": round(obj.decimal_odds, 2) if hasattr(obj, "decimal_odds") else None,
            "american": odds_data,
            "fractional": getattr(obj, "fractional_odds", None),
        }

    # ---------- PROFILE FIELD GETTERS ----------
    def get_profile(self, obj):
        """Safely fetch user profile or return None."""
        return getattr(obj.user, "profile", None)

    def get_crs_risk_score(self, obj):
        profile = self.get_profile(obj)
        return float(profile.crs_risk_score) if profile and profile.crs_risk_score is not None else None

    def get_crs_risk_level(self, obj):
        profile = self.get_profile(obj)
        return profile.crs_risk_level if profile else None

    def get_max_wager_pct(self, obj):
        """
        Returns max_wager as a percentage of total risk exposure limit
        (based on CRS-adjusted exposure, not allowable profit).
        """
        profile = self.get_profile(obj)
        if not profile:
            return None

        settings = PlatformSettings.get_instance()
        exposure_limit = profile.crs_risk_score * settings.base_exposure_limit
        if exposure_limit <= 0:
            return None

        percentage = (profile.max_stake / exposure_limit) * 100
        return round(float(percentage), 2)

    def get_allowable_profit(self, obj):
        profile = self.get_profile(obj)
        return float(profile.allowable_profit) if profile and profile.allowable_profit is not None else None



class MarketVigAdjustmentSerializer(serializers.Serializer):
    """
    Serializer for the input to the MarketVigAdjustmentAPIView.
    """

    market_id = serializers.IntegerField(
        help_text="The ID of the market to adjust vig for."
    )
    new_vig_percentage = serializers.DecimalField(
        max_digits=5,  # e.g., 0.05 for 5%, up to 99.99% if needed
        decimal_places=4,
        min_value=Decimal("0.00"),  # Vig can be 0%
        max_value=Decimal("0.99"),  # Max 99% vig (realistic upper bound)
        help_text="The new vig percentage to apply (e.g., 0.045 for 4.5%).",
    )


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Profile
        fields = ["id", "username", "customer_risk_score", "balance"]
        read_only_fields = [
            "id",
            "username",
            "balance",
        ]  # Balance is updated by bet logic, not directly here


# Serializer for CRS adjustment input
class CRSAdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(
        help_text="The ID of the user whose CRS to adjust."
    )
    new_crs = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
        help_text="The new Customer Risk Score (0.00 to 100.00).",
    )
    reason = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Reason for CRS adjustment.",
    )


# Serializer for OddsAdjustmentLog (read-only)
class OddsAdjustmentLogSerializer(serializers.ModelSerializer):
    market_id = serializers.IntegerField(source="market.id", read_only=True)
    market_description = serializers.CharField(source="market.__str__", read_only=True)
    admin_username = serializers.CharField(source="admin_user.username", read_only=True)

    class Meta:
        model = BetOverrideLog
        fields = [
            "id",
            "market_id",
            "market_description",
            "admin_username",
            "old_display_odds_over",
            "old_display_odds_under",
            "new_display_odds_over",
            "new_display_odds_under",
            "adjusted_at",
        ]


# Serializer for BetOverrideLog (read-only)
class BetOverrideLogSerializer(serializers.ModelSerializer):
    bet_id = serializers.IntegerField(source="bet.id", read_only=True)
    bet_description = serializers.CharField(
        source="bet.__str__", read_only=True
    )  # Using __str__ for display
    admin_username = serializers.CharField(source="admin_user.username", read_only=True)
    user_username = serializers.CharField(source="bet.user.username", read_only=True)

    class Meta:
        model = BetOverrideLog
        fields = [
            "id",
            "bet_id",
            "bet_description",
            "user_username",
            "admin_username",
            "old_status",
            "new_status",
            "old_payout_amount",
            "new_payout_amount",
            "reason",
            "overridden_at",
        ]


# Serializer for BetOverride Action (input)
class BetOverrideActionSerializer(serializers.Serializer):
    bet_id = serializers.IntegerField(help_text="The ID of the bet to override.")
    new_status = serializers.ChoiceField(
        choices=Bet.BET_STATUS_CHOICES,
        help_text="The new status for the bet (e.g., 'won', 'lost', 'void').",
    )
    new_payout_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
        help_text="Optional: New payout amount if status is 'won'. Defaults to calculated payout.",
    )
    reason = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Reason for the bet override.",
    )

    def validate(self, data):
        new_status = data.get("new_status")
        new_payout_amount = data.get("new_payout_amount")

        if new_status == "won" and new_payout_amount is None:
            # If status is won, payout amount should typically be provided or calculated.
            # We'll make it optional here as it might be handled by the view logic.
            pass
        elif new_status in ["lost", "void"] and new_payout_amount is not None:
            if new_payout_amount > Decimal("0.00"):
                raise serializers.ValidationError(
                    {
                        "new_payout_amount": "Payout amount must be 0 for 'lost' or 'void' bets."
                    }
                )
        return data


# Serializer for CRSModificationLog (read-only)
class CRSModificationLogSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user_profile.user.id", read_only=True)
    username = serializers.CharField(
        source="user_profile.user.username", read_only=True
    )
    admin_username = serializers.CharField(source="admin_user.username", read_only=True)

    class Meta:
        model = CRSModificationLog
        fields = [
            "id",
            "user_id",
            "username",
            "admin_username",
            "old_crs",
            "new_crs",
            "reason",
            "modified_at",
        ]


# Serializer for Liability Monitoring
class LiabilityItemSerializer(serializers.Serializer):
    stock = serializers.CharField()
    expiry = serializers.DateField()
    target_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    outcome = serializers.CharField()
    total_wagered_pending = serializers.DecimalField(max_digits=10, decimal_places=2)
    # potential_payout_if_wins = serializers.DecimalField(max_digits=10, decimal_places=2, required=False) # If you add this calculation


# Serializer for PnL Report
class UserPnLSerializer(serializers.Serializer):
    username = serializers.CharField()
    total_net_pnl = serializers.DecimalField(max_digits=12, decimal_places=2)


# Serializer for recent bets (lightweight)
class RecentBetSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    market_symbol = serializers.CharField(source="market.stock.symbol", read_only=True)
    market_target_price = serializers.DecimalField(
        source="market.target_price", max_digits=10, decimal_places=2, read_only=True
    )
    market_expiry_date = serializers.DateField(
        source="market.expiry_date", read_only=True
    )

    class Meta:
        model = Bet

class SuspendedMarketSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.CharField(source="stock.symbol", read_only=True)
    stock_company_name = serializers.CharField(source="stock.company_name", read_only=True)
    stock_url = serializers.CharField(source="stock.url", read_only=True)
    net_exposure = serializers.SerializerMethodField(read_only=True)

    def get_net_exposure(self, obj):
        return str(obj.net_exposure)

    class Meta:
        model = Market
        fields = [
            "id",
            "stock_symbol",
            "stock_url",
            "stock_company_name",
            "target_price",
            "expiry_date",
            "outcome_type",
            "display_odds_over",
            "display_odds_under",
            "implied_odds_over",
            "implied_odds_under",
            "net_exposure",
            "is_active",
            "is_suspended_over",
            "is_suspended_under",
            "requires_admin_override",
            "nudge_offset_over",
            "nudge_offset_under",
        ]


class SuspendedMarketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Market
        fields = [
            "is_active",
            "is_suspended_over",
            "is_suspended_under",
            "requires_admin_override",
        ]

    def validate(self, data):
        # Ensure boolean-like values are correct types
        for k in ["is_active", "is_suspended_over", "is_suspended_under", "requires_admin_override"]:
            if k in data and not isinstance(data[k], bool):
                # allow values like 'true'/'false' from clients by coercion
                val = data[k]
                if isinstance(val, str):
                    lowered = val.lower()
                    if lowered in ["true", "1", "yes", "y"]:
                        data[k] = True
                    elif lowered in ["false", "0", "no", "n"]:
                        data[k] = False
                    else:
                        raise serializers.ValidationError({k: "Invalid boolean value"})
                else:
                    raise serializers.ValidationError({k: "Invalid boolean value"})
        return data


class MarketCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new Market instances.
    Requires 'stock_symbol' as a write-only field to lookup the Stock object.
    """

    stock_symbol = serializers.CharField(
        write_only=True, help_text="Symbol of the stock (e.g., AAPL)"
    )

    class Meta:
        model = Market
        fields = [
            "stock_symbol",
            "target_price",
            "expiry_date",
            "outcome_type",
            "is_active",
            # Implied and display odds can be set via initial values or a separate update,
            # so they are not required for creation here.
        ]
        read_only_fields = [
            "implied_odds_over",
            "implied_odds_under",
            "display_odds_over",
            "display_odds_under",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        """
        Custom validation to ensure the stock_symbol exists and outcome_type is valid.
        """
        stock_symbol = data.get("stock_symbol")
        outcome_type = data.get("outcome_type")

        if not Stock.objects.filter(symbol=stock_symbol).exists():
            raise serializers.ValidationError(
                {"stock_symbol": "Stock with this symbol does not exist."}
            )

        if outcome_type not in ["over", "under"]:
            raise serializers.ValidationError(
                {"outcome_type": "Outcome type must be 'over' or 'under'."}
            )

        # Check for uniqueness if trying to create an identical market
        stock = Stock.objects.get(symbol=stock_symbol)
        if Market.objects.filter(
            stock=stock,
            target_price=data.get("target_price"),
            expiry_date=data.get("expiry_date"),
            outcome_type=outcome_type,
        ).exists():
            raise serializers.ValidationError(
                "A market with these exact parameters already exists."
            )

        return data

    def create(self, validated_data):
        """
        Override create to handle the stock_symbol to Stock object conversion.
        """
        stock_symbol = validated_data.pop("stock_symbol")
        stock = Stock.objects.get(symbol=stock_symbol)

        # Set initial odds to a default (they will be updated later by a command)
        validated_data["implied_odds_over"] = Decimal("0.5")
        validated_data["implied_odds_under"] = Decimal("0.5")
        validated_data["display_odds_over"] = "+100"
        validated_data["display_odds_under"] = "+100"

        market = Market.objects.create(stock=stock, **validated_data)
        return market


class MarketUpdateOddsSerializer(serializers.Serializer):
    """
    Serializer for updating market odds.
    Can accept a specific market ID or trigger for all active markets.
    """

    market_id = serializers.IntegerField(
        required=False,
        help_text="Optional: ID of a specific market to update. If omitted, all active markets will be processed.",
    )


class MarketResolveSerializer(serializers.Serializer):
    """
    Serializer for resolving expired markets.
    Can accept a specific expiry date OR a specific market ID.
    """

    expiry_date = serializers.DateField(
        required=False,
        help_text="Optional: Resolve markets that expired on or before this date (YYYY-MM-DD).",
    )
    market_id = serializers.IntegerField(
        required=False, help_text="Optional: ID of a specific market to resolve."
    )

    def validate(self, data):
        """
        Ensure either expiry_date OR market_id is provided, but not both or neither.
        """
        expiry_date = data.get("expiry_date")
        market_id = data.get("market_id")

        if not expiry_date and not market_id:
            raise serializers.ValidationError(
                "Either 'expiry_date' or 'market_id' must be provided."
            )
        if expiry_date and market_id:
            raise serializers.ValidationError(
                "Cannot provide both 'expiry_date' and 'market_id'. Choose one resolution scope."
            )

        return data


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new administrative user.
    Requires password confirmation for security.
    """

    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password_confirm",
            "is_staff",
            "is_superuser",
        )
        # You might want to remove 'is_staff' and 'is_superuser' from 'fields'
        # if you always want them to be True and not controlled by input,
        # but for flexibility, we'll keep them here with validation.

    def validate(self, data):
        """
        Validate that passwords match and that is_staff/is_superuser are set.
        """
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        # Ensure that is_staff and is_superuser are explicitly set to True
        # to prevent accidental non-admin user creation via this endpoint.
        # This makes the endpoint's purpose explicit: to create an admin.
        if not data.get("is_staff", False):
            raise serializers.ValidationError(
                {"is_staff": "Admin user must have 'is_staff' set to true."}
            )
        if not data.get("is_superuser", False):
            raise serializers.ValidationError(
                {"is_superuser": "Admin user must have 'is_superuser' set to true."}
            )

        return data

    def create(self, validated_data):
        """
        Create a new User instance and set the password correctly.
        """
        validated_data.pop("password_confirm")  # Remove confirm field
        password = validated_data.pop("password")  # Get password before creating user

        user = User.objects.create(**validated_data)
        user.set_password(password)  # Set hashed password
        user.save()
        return user
