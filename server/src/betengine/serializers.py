# betting/serializers/bet.py
import logging
from datetime import date
from decimal import Decimal
from django.db import transaction

import requests
from rest_framework import serializers

from betengine.utils import calculate_payout, convert_odds
from mkt.serializers import StockSerializer
from user.models import CompetitionMember

from .models import Bet, Competition, CompetitionStatus, Market, ParlayBet, Stock

logger = logging.getLogger(__name__)


def get_user_preference(request):
    if request and request.user and request.user.is_authenticated:
        # print("AUTH USER:", request.user)
        # print("PROFILE:", getattr(request.user, "profile", None))
        # print("PREFERENCE:", getattr(request.user.profile, "betting_preference", "decimal"))
        return getattr(request.user.profile, "betting_preference", "decimal")
    return "decimal"

class MarketSerializer(serializers.ModelSerializer):
    odds_over = serializers.SerializerMethodField(read_only=True)
    odds_under = serializers.SerializerMethodField(read_only=True)
    net_exposure = serializers.SerializerMethodField(read_only=True)
    stock = StockSerializer()

    class Meta:
        model = Market
        fields = [
            "id",
            "stock",
            "target_price",
            "expiry_date",
            "outcome_type",
            "implied_odds_over",
            "implied_odds_under",
            "is_active",
            "exposure_over",
            "exposure_under",
            "net_exposure",
            "requires_admin_override",
            "odds_over",
            "odds_under",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "odds_over",
            "odds_under",
        ]

    def get_odds_over(self, obj):
        return {
            "american": obj.display_odds_over,
            "decimal": str(obj.display_odds_over_decimal) if obj.display_odds_over_decimal is not None else None,
            "fractional": obj.display_odds_over_fractional,
        }

    def get_odds_under(self, obj):
        return {
            "american": obj.display_odds_under,
            "decimal": str(obj.display_odds_under_decimal) if obj.display_odds_under_decimal is not None else None,
            "fractional": obj.display_odds_under_fractional,
        }

    def get_net_exposure(self, obj):
        return str(obj.net_exposure)
    
class MarketOddsSerializer(serializers.ModelSerializer):
    stock = StockSerializer()
    expiry_date = serializers.SerializerMethodField()
    odds_over = serializers.SerializerMethodField()
    odds_under = serializers.SerializerMethodField()
    net_exposure = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Market
        fields = [
            'id', 'stock', 'target_price', 'expiry_date', 'outcome_type',
            'implied_odds_over', 'implied_odds_under', 'is_active',
            'exposure_over', 'exposure_under', 'net_exposure', 'requires_admin_override',
            'odds_over', 'odds_under'
        ]

    def get_expiry_date(self, obj):
        return obj.expiry_date.strftime("%a, %d %b %Y")

    def get_odds_over(self, obj):
        return self._build_odds_object(
            display_american=obj.display_odds_over,
            display_decimal=(
                f"{obj.display_odds_over_decimal:.2f}"
                if obj.display_odds_over_decimal is not None else None
            ),
            display_fractional=obj.display_odds_over_fractional
        )

    def get_odds_under(self, obj):
        return self._build_odds_object(
            display_american=obj.display_odds_under,
            display_decimal=(
                f"{obj.display_odds_under_decimal:.2f}"
                if obj.display_odds_under_decimal is not None else None
            ),
            display_fractional=obj.display_odds_under_fractional
        )

    def _build_odds_object(self, display_american, display_decimal, display_fractional):
        request = self.context.get("request")
        preference = get_user_preference(request) or "decimal"

        # Safe fallback for nulls
        american = display_american if display_american else None
        decimal = str(display_decimal) if display_decimal else None
        fractional = display_fractional if display_fractional else None

        preferred_value = {
            "decimal": decimal,
            "american": american,
            "fractional": fractional,
        }.get(preference)

        return {
            "american": american,
            "decimal": decimal,
            "fractional": fractional,
            "preferred": {
                "format": preference,
                "value": preferred_value
            }
        }

    def get_net_exposure(self, obj):
        return str(obj.net_exposure)


class CompetitionSerializer(serializers.ModelSerializer):
    creator_username = serializers.CharField(source="creator.username", read_only=True)
    member_count = serializers.SerializerMethodField(read_only=True)
    is_registration_open = serializers.BooleanField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    user_joined = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Competition
        fields = [
            "id",
            "name",
            "description",
            "creator",
            "creator_username",
            "max_members",
            "member_count",
            "start_date",
            "end_date",
            "registration_close_date",
            "status",
            "entry_fee",
            "scoring_method",
            "is_private",
            "is_registration_open",
            "is_full",
            "user_joined",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "creator",
            "creator_username",
            "member_count",
            "is_registration_open",
            "is_full",
            "user_joined",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        registration_close_date = attrs.get(
            "registration_close_date",
            getattr(self.instance, "registration_close_date", None),
        )

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError(
                {"end_date": "end_date must be later than start_date."}
            )

        if registration_close_date and start_date and registration_close_date > start_date:
            raise serializers.ValidationError(
                {
                    "registration_close_date": (
                        "registration_close_date must be on or before start_date."
                    )
                }
            )

        return attrs

    def get_member_count(self, obj):
        annotated_count = getattr(obj, "member_count", None)
        if annotated_count is not None:
            return annotated_count
        return obj.members.count()

    def get_user_joined(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.members.filter(user=request.user).exists()


class CompetitionMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    competition_name = serializers.CharField(source="competition.name", read_only=True)

    class Meta:
        model = CompetitionMember
        fields = [
            "id",
            "competition",
            "competition_name",
            "user",
            "username",
            "joined_at",
            "final_rank",
            "final_score",
            "is_disqualified",
        ]
        read_only_fields = fields


class CompetitionLeaderboardEntrySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    total_bets = serializers.SerializerMethodField()
    net_profit = serializers.SerializerMethodField()
    roi = serializers.SerializerMethodField()
    win_rate = serializers.SerializerMethodField()

    class Meta:
        model = CompetitionMember
        fields = [
            "id",
            "user",
            "username",
            "joined_at",
            "final_rank",
            "final_score",
            "total_bets",
            "net_profit",
            "roi",
            "win_rate",
        ]
        read_only_fields = fields

    def _stats(self, obj):
        if not hasattr(obj, "_cached_member_stats"):
            obj._cached_member_stats = obj.get_member_stats()
        return obj._cached_member_stats

    def get_total_bets(self, obj):
        return self._stats(obj).get("total_bets")

    def get_net_profit(self, obj):
        return self._stats(obj).get("net_profit")

    def get_roi(self, obj):
        return self._stats(obj).get("roi")

    def get_win_rate(self, obj):
        return self._stats(obj).get("win_rate")


class CompetitionJoinSerializer(serializers.Serializer):
    competition_id = serializers.IntegerField(read_only=True)
    joined = serializers.BooleanField(read_only=True)
    current_member_count = serializers.IntegerField(read_only=True)
    max_members = serializers.IntegerField(read_only=True)
    message = serializers.CharField(read_only=True)

    
class BetSerializer(serializers.ModelSerializer):
    market_details = MarketSerializer(source="market", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    potential_payout = serializers.SerializerMethodField()

    class Meta:
        model = Bet
        fields = [
            "id",
            "username",
            "market_details",
            "amount_wagered",
            "odds_at_placement",
            "chosen_outcome",
            "status",
            "payout_amount",
            "potential_payout",
            "is_parlay_leg",
            "parlay_bet",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "payout_amount",
            "potential_payout",
            "is_parlay_leg",
            "parlay_bet",
            "created_at",
        ]

    def get_potential_payout(self, obj):
        try:
            return round(obj.get_potential_payout(), 2)
        except Exception:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        # Determine preferred odds format
        preference = get_user_preference(request)

        # Convert using your existing utils function
        data["odds_at_placement"] = convert_odds(
            odds=instance.odds_at_placement,
            to_format=preference
        )
        return data
# class BetSerializer(serializers.ModelSerializer):
#     market_details = MarketSerializer(source="market", read_only=True)
#     username = serializers.CharField(source="user.username", read_only=True)
#     potential_payout = serializers.SerializerMethodField()

#     class Meta:
#         model = Bet
#         fields = [
#             "id",
#             "username",
#             "market_details",
#             "amount_wagered",
#             "odds_at_placement",
#             "chosen_outcome",
#             "status",
#             "payout_amount",
#             "potential_payout",
#             "is_parlay_leg",
#             "parlay_bet",
#             "created_at",
#         ]
#         read_only_fields = [
#             "status",
#             "payout_amount",
#             "potential_payout",
#             "is_parlay_leg",
#             "parlay_bet",
#             "created_at",
#         ]

#     def get_potential_payout(self, obj):
#         try:
#             return round(obj.get_potential_payout(), 2)
#         except Exception:
#             return None
        
class ParlayBetSerializer(serializers.ModelSerializer):
    legs = BetSerializer(many=True, read_only=True)
    potential_payout = serializers.SerializerMethodField()
    combined_decimal_odds = serializers.SerializerMethodField()

    class Meta:
        model = ParlayBet
        fields = [
            "id",
            "user",
            "amount_wagered",
            "combined_odds",           # Optional: keep if still useful
            "combined_decimal_odds",   # Newly calculated decimal odds
            "status",
            "payout_amount",
            "potential_payout",
            "legs",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "payout_amount",
            "potential_payout",
            "legs",
            "created_at",
            "combined_decimal_odds",
        ]

    def get_potential_payout(self, obj):
        try:
            return round(obj.get_potential_payout(), 2)
        except Exception:
            return None

    def get_combined_decimal_odds(self, obj):
        try:
            return round(obj.get_combined_decimal_odds(), 2)
        except Exception:
            return None

# betting/serializers/bet_response.py
class BetResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bet
        fields = [
            "id",
            "status",
            "odds",
            "stake",
            "target_price",
            "bet_type",
            "symbol",
            "placed_at",
        ]


class BetPlacementSerializer(serializers.ModelSerializer):
    # market_id is an input field representing the Market instance
    market_id = serializers.PrimaryKeyRelatedField(
        queryset=Market.objects.all(),  # Queryset to resolve ID to Market instance
        source="market",  # Maps 'market_id' input to 'market' field on Bet model
        write_only=True,  # This field is for input only
        help_text="The ID of the market you are placing a bet on.",
    )
    # chosen_outcome is an input field
    chosen_outcome = serializers.ChoiceField(
        choices=[("over", "Over"), ("under", "Under")],
        write_only=True,  # This field is for input only
        help_text="Your chosen outcome ('over' or 'under').",
    )
    # amount_wagered is an input field
    amount_wagered = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),  # Minimum bet amount
        write_only=True,  # This field is for input only
        help_text="The amount of money you want to wager on this bet.",
    )

    class Meta:
        model = Bet
        # Fields that will be sent in the POST request:
        fields = [
            "market_id",
            "chosen_outcome",
            "amount_wagered",
            "id",
            "odds_at_placement",
            "payout_amount",
            "status",
            "created_at",
        ]
        # These fields are set internally, not directly by the user input
        read_only_fields = [
            "id",
            "odds_at_placement",
            "payout_amount",
            "status",
            "created_at",
        ]

    def validate(self, data):
        """
        Validates the input data and prepares additional data for Bet creation.
        """
        market = data.get("market")  # Resolved Market instance from market_id
        chosen_outcome = data.get("chosen_outcome")
        amount_wagered = data.get("amount_wagered")
        user = self.context[
            "request"
        ].user  # Access the current user from the request context

        # 1. Basic checks for required fields (though DRF's default validation often covers this)
        if not market:
            raise serializers.ValidationError({"market_id": "Market ID is required."})
        if not chosen_outcome:
            raise serializers.ValidationError(
                {"chosen_outcome": "Chosen outcome is required."}
            )
        if (
            amount_wagered is None
        ):  # Use is None for DecimalField as 0 is a valid Decimal value
            raise serializers.ValidationError(
                {"amount_wagered": "Amount wagered is required."}
            )
        # 2. Validate Market state
        if not market.is_active:
            raise serializers.ValidationError(
                {"market_id": "This market is currently not active for betting."}
            )
        # Ensure current time is considered for expiry
        if market.expiry_date <= date.today():
            raise serializers.ValidationError(
                {"market_id": "This market has already expired."}
            )

        # 3. Determine the odds_at_placement
        if chosen_outcome == "over":
            odds_str = market.display_odds_over
        elif chosen_outcome == "under":
            odds_str = market.display_odds_under
        else:
            # Should be caught by ChoiceField, but a safeguard
            raise serializers.ValidationError(
                {"chosen_outcome": "Invalid outcome choice. Must be 'over' or 'under'."}
            )

        if not odds_str:
            raise serializers.ValidationError(
                f"Odds for '{chosen_outcome}' are not available for this market."
            )

        # Attach `odds_at_placement` to validated_data for Bet creation
        data["odds_at_placement"] = odds_str

        # 4. Calculate potential payout
        payout = calculate_payout(amount_wagered, odds_str)
        if payout <= Decimal("0.00"):
            raise serializers.ValidationError(
                {
                    "amount_wagered": "Could not calculate a valid payout with the provided odds or amount."
                }
            )
        # Attach `payout_amount` to validated_data for Bet creation
        data["payout_amount"] = payout

        # 5. User balance check (CRITICAL TODO: Implement real balance logic here)
        # This is a placeholder. You would typically have a Wallet or Profile model
        # associated with the User model, holding their balance.
        # Example:
        # if user.userprofile.balance < amount_wagered:
        #     raise serializers.ValidationError({"amount_wagered": "Insufficient funds in your account."})

        # Attach the user to validated_data for Bet creation
        data["user"] = user

        return data

    def create(self, validated_data):
        """
        Create and return a new `Bet` instance, given the validated data.
        This method will also handle fund deduction (placeholder).
        """
        # Extract fields needed for Bet creation.
        # These are guaranteed to be present and valid by the validate() method.
        user = validated_data["user"]
        market = validated_data["market"]
        amount_wagered = validated_data["amount_wagered"]
        chosen_outcome = validated_data["chosen_outcome"]
        odds_at_placement = validated_data["odds_at_placement"]
        payout_amount = validated_data["payout_amount"]

        # --- IMPORTANT: BEGIN ATOMIC TRANSACTION ---
        # This ensures that either the bet is created AND funds are deducted, or neither happens.
        with transaction.atomic():
            # TODO: Actual fund deduction logic goes here.
            # Example (assuming user has a related UserProfile with a 'balance' field):
            # user_profile = user.userprofile
            # if user_profile.balance < amount_wagered:
            #    # This case should ideally be caught by serializer.validate(), but good to have
            #    raise serializers.ValidationError("Insufficient balance for this bet.")
            # user_profile.balance -= amount_wagered
            # user_profile.save()
            logger.info(
                f"Deducting {amount_wagered} from user {user.username}'s balance. (Placeholder)"
            )

            # Create the Bet instance
            bet = Bet.objects.create(
                user=user,
                market=market,
                amount_wagered=amount_wagered,
                chosen_outcome=chosen_outcome,
                odds_at_placement=odds_at_placement,
                payout_amount=payout_amount,
                status="pending",  # Bets always start as pending
                is_parlay_leg=False,  # Default for single bets
                parlay_bet=None,  # Explicitly set to None for single bets
            )
        # --- END ATOMIC TRANSACTION ---

        return bet


# market_data/serializers.py (add this if it's not there)
class BetResolutionSerializer(serializers.Serializer):
    bet_id = serializers.IntegerField(help_text="The ID of the bet to resolve.")


class ParlayBetResolutionSerializer(serializers.Serializer):
    """
    Serializer for the input to the ParlayBetResolutionAPIView.
    """

    parlay_bet_id = serializers.IntegerField(
        help_text="The ID of the parlay bet to resolve."
    )

class StockAdminSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    change = serializers.SerializerMethodField()
    percent_change = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            "id",
            "company_name",
            "symbol",
            "price",
            "change",
            "percent_change",
            "market_status",
            "auto_odds",
            "url",
        ]

    def get_price(self, obj):
        if obj.last_price:
            return f"${obj.last_price:.2f}"
        obj.get_current_price()  # fetch and cache
        return f"${obj.last_price or 0:.2f}"

    def get_change(self, obj):
        return f"{obj.last_change or 0.00:.2f}"

    def get_percent_change(self, obj):
        return obj.last_percent_change or "0.00%"