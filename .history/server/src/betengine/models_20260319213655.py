# betengine/models.py

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.contrib.auth import get_user_model
from django.conf import settings
from mkt.market_chart import ODDS_LADDER_JSON
from django.db import models, transaction
from taggit.managers import TaggableManager
from betengine.utils import american_to_decimal_odds, american_to_fractional_odds, implied_probability_to_american
from django.core.cache import cache
from django.utils import timezone
import requests
from math import gcd

from mkt.utils import get_side_and_american_odds
User = get_user_model()


def round_two_places(value):
    return float(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))



class Stock(models.Model):
    """
    Represents an underlying stock ticker.
    """

    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    url = models.URLField(max_length=200, blank=True, null=True, help_text="logo url for the stock")
    market_status = models.BooleanField(default=True)
    auto_odds = models.BooleanField(default=True)
    last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_change = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_percent_change = models.CharField(max_length=10, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tags = TaggableManager()

    def __str__(self):
        return self.symbol
    
    def get_current_price(self, api_key: str = None):

        api_key = api_key or getattr(settings, "ALPHA_VANTAGE_API_KEY", None)
        if not api_key:
            return Decimal("0")

        url = "https://www.alphavantage.co/query"
        params = {"function": "GLOBAL_QUOTE", "symbol": self.symbol, "apikey": api_key}

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json().get("Global Quote", {})
            price_str = data.get("05. price")
            change_str = data.get("09. change")
            percent_str = data.get("10. change percent")

            if price_str:
                self.last_price = Decimal(price_str)
            if change_str:
                self.last_change = Decimal(change_str)
            if percent_str:
                self.last_percent_change = percent_str

            self.save(update_fields=["last_price", "last_change", "last_percent_change"])
            return self.last_price or Decimal("0")
        except Exception:
            return self.last_price or Decimal("0")

    class Meta:
        verbose_name_plural = "Stocks"

class Market(models.Model):
    """
    Represents a specific betting market or prediction on a stock's price.
    e.g., "AAPL will be > $180 by 2025-12-31"
    """
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    target_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Target price for the prediction (e.g., $180.00)",
    )
    expiry_date = models.DateField(
        help_text="The date by which the target price needs to be reached or exceeded."
    )
    outcome_type = models.CharField(
        max_length=10,
        default="over",
        choices=[("over", "Over"), ("under", "Under")],
        help_text="The type of outcome predicted (e.g., 'over' target price, 'under' target price)",
    )
    implied_odds_over = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.00"),
        help_text="Implied probability/odds for 'over' target (e.g., 0.65 for 65%)",
    )
    implied_odds_under = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.00"),
        help_text="Implied probability/odds for 'under' target",
    )
    display_odds_over = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Odds for 'over' in American format (e.g., -110)",
    )
    display_odds_under = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Odds for 'under' in American format",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this betting market is currently open for bets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    ladder_favored_side = models.CharField(max_length=10, choices=[("over", "Over"), ("under", "Under")], null=True, blank=True)
    total_volume = models.PositiveIntegerField(default=0)
    br_true_percent_over = models.IntegerField(default=50)
    br_true_percent_under = models.IntegerField(default=50)
    # Persistent offsets (keep nudges across new odds updates)
    nudge_offset_over = models.SmallIntegerField(default=0, help_text="Cumulative nudge offset for Over side")
    nudge_offset_under = models.SmallIntegerField(default=0, help_text="Cumulative nudge offset for Under side")
    feed_implied_odds_over = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.00"), help_text="Raw implied probability for 'over' from latest Alpha Vantage feed.")
    feed_implied_odds_under = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.00"), help_text="Raw implied probability for 'under' from latest Alpha Vantage feed.")
    net_effective_nudge_over = models.SmallIntegerField(default=0, help_text="Net effective nudge for Over side")
    net_effective_nudge_under = models.SmallIntegerField(default=0, help_text="Net effective nudge for Under side")

    baseline_prob_over = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.00"), help_text="Initial feed-based probability for over before any nudging")
    baseline_prob_under = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.00"), help_text="Initial feed-based probability for under before any nudging")

    max_risk_tolerance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal("3000.00"),
        help_text="Per-market maximum allowed net exposure. Uses platform default when null.",
    )
    exposure_over = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), help_text="Total liability exposure for Over side.")
    exposure_under = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), help_text="Total liability exposure for Under side.")
    is_suspended_over = models.BooleanField(default=False)
    is_suspended_under = models.BooleanField(default=False)
    requires_admin_override = models.BooleanField(default=False, help_text="True if market was auto-suspended due to max exposure.")
    
    @property
    def display_odds_over_fractional(self):
        if self.display_odds_over:
            return american_to_fractional_odds(self.display_odds_over)
        return None

    @property
    def display_odds_over_decimal(self):
        if self.display_odds_over:
            return round_two_places(american_to_decimal_odds(self.display_odds_over))
        return None

    @property
    def display_odds_under_fractional(self):
        if self.display_odds_under:
            return american_to_fractional_odds(self.display_odds_under)
        return None

    @property
    def display_odds_under_decimal(self):
        if self.display_odds_under:
            return round_two_places(american_to_decimal_odds(self.display_odds_under))
        return None

    @property
    def implied_odds_over_rounded(self):
        return round_two_places(self.implied_odds_over)

    @property
    def implied_odds_under_rounded(self):
        return round_two_places(self.implied_odds_under)

    @property
    def net_exposure(self):
        """
        Returns the net exposure as the absolute difference between over and under sides.
        This allows hedging: high exposure on both sides = lower net risk due to offsetting positions.
        Only one outcome can occur, so the net risk is the difference between unmatched exposures.
        """
        return abs(self.exposure_over - self.exposure_under)

    class Meta:
        unique_together = ("stock", "target_price", "expiry_date", "outcome_type")
        ordering = ["target_price", "-expiry_date", "stock__symbol"]
        verbose_name_plural = "Markets"

    def __str__(self):
        return f"{self.stock.symbol} {self.outcome_type.capitalize()} ${self.target_price} by {self.expiry_date.strftime('%Y-%m-%d')}"
    
    def _apply_new_odds(self):
        """
        Refreshes American odds from current implied probabilities using fixed vig.
        """
        vig = Decimal("9.0")
        side_over, american_over = get_side_and_american_odds(self.implied_odds_over, ODDS_LADDER_JSON, vig)
        side_under, american_under = get_side_and_american_odds(self.implied_odds_under, ODDS_LADDER_JSON, vig)

        self.display_odds_over = str(american_over)
        self.display_odds_under = str(american_under)
    def _compute_balanced_probs(self, base_over: Decimal, base_under: Decimal, net_nudge_over: int, net_nudge_under: int) -> tuple[Decimal, Decimal]:
        """
        Computes balanced over/under probabilities ensuring they always sum to 1.00.
        Nudges are interpreted as integer percent shifts (±n).
        
        Logic:
        - Positive nudge increases probability of the side nudged.
        - Total probability always sums to 100%.
        """
        # Base probabilities in percent
        over_percent = float(base_over) * 100
        under_percent = float(base_under) * 100

        # Apply nudges independently
        new_over_percent = over_percent + net_nudge_over
        new_under_percent = under_percent + net_nudge_under

        # Ensure sum is 100%
        total_percent = new_over_percent + new_under_percent
        if total_percent != 100:
            correction = 100 - total_percent
            # Apply correction proportionally to both sides
            new_over_percent += correction * (new_over_percent / total_percent)
            new_under_percent += correction * (new_under_percent / total_percent)

        # Clip to valid range [1%, 99%] to avoid extreme probabilities
        new_over_percent = max(1, min(new_over_percent, 99))
        new_under_percent = 100 - new_over_percent

        return (
            Decimal(str(new_over_percent / 100)).quantize(Decimal("0.0001")),
            Decimal(str(new_under_percent / 100)).quantize(Decimal("0.0001")),
        )

    @transaction.atomic
    def apply_nudge(self, side: str, direction: int, user=None):
        """
        Applies a nudge (+/-) to over or under side, recalculates probabilities and American odds.
        """
        from admin_panel.models import MarketNudgeHistory

        if side not in ["over", "under"]:
            raise ValueError("side must be 'over' or 'under'")

        # --- 1️⃣ Update net effective nudges ---
        if side == "over":
            self.net_effective_nudge_over += direction
            self.nudge_offset_over += direction
        else:
            self.net_effective_nudge_under += direction
            self.nudge_offset_under += direction

        # --- 2️⃣ Compute balanced probabilities using baseline feed ---
        base_over = self.feed_implied_odds_over or self.baseline_prob_over or self.implied_odds_over
        base_under = self.feed_implied_odds_under or self.baseline_prob_under or self.implied_odds_under

        new_prob_over, new_prob_under = self._compute_balanced_probs(
            base_over,
            base_under,
            self.net_effective_nudge_over,
            self.net_effective_nudge_under,
        )

        self.implied_odds_over = new_prob_over
        self.implied_odds_under = new_prob_under

        # --- 3️⃣ Update American odds using ladder (vig fixed) ---
        self._apply_new_odds()

        # --- 4️⃣ Persist ---
        self.save(update_fields=[
            "implied_odds_over",
            "implied_odds_under",
            "display_odds_over",
            "display_odds_under",
            "net_effective_nudge_over",
            "net_effective_nudge_under",
            "nudge_offset_over",
            "nudge_offset_under",
            "updated_at",
        ])

        # --- 5️⃣ Log nudge history ---
        MarketNudgeHistory.objects.create(
            market=self,
            stock=self.stock,
            side=side,
            direction=direction,
            previous_display_odds=f"{self.display_odds_over if side=='over' else self.display_odds_under}",
            new_display_odds=f"{self.display_odds_over if side=='over' else self.display_odds_under}",
            created_by=user,
        )

        # --- 6️⃣ Clear cached market data ---
        cache.delete(f"market_grouped_{self.stock.symbol}")

        return self
    @transaction.atomic
    def reset_nudges(self):
        """
        Resets all nudges back to baseline feed values, recomputes American odds,
        and recalculates probabilities using _compute_balanced_probs for consistency.
        """
        # --- 1️⃣ Clear net effective nudges ---
        self.net_effective_nudge_over = 0
        self.net_effective_nudge_under = 0

        # --- 2️⃣ Use baseline feed probabilities ---
        base_over = self.feed_implied_odds_over or self.baseline_prob_over or self.implied_odds_over
        base_under = self.feed_implied_odds_under or self.baseline_prob_under or self.implied_odds_under

        # --- 3️⃣ Recompute balanced probabilities as if no nudges applied ---
        new_prob_over, new_prob_under = self._compute_balanced_probs(
            base_over,
            base_under,
            self.net_effective_nudge_over,
            self.net_effective_nudge_under,
        )

        self.implied_odds_over = new_prob_over
        self.implied_odds_under = new_prob_under

        # --- 4️⃣ Update American odds using ladder (vig fixed at 9.0) ---
        self._apply_new_odds()

        # --- 5️⃣ Persist changes ---
        self.save(update_fields=[
            "net_effective_nudge_over",
            "net_effective_nudge_under",
            "implied_odds_over",
            "implied_odds_under",
            "display_odds_over",
            "display_odds_under",
            "updated_at",
        ])

        # --- 6️⃣ Clear cache ---
        cache.delete(f"market_grouped_{self.stock.symbol}")

        return self

# New Model: ParlayBet (for grouping multiple bets)
class ParlayBet(models.Model):
    """
    Represents a parlay bet, composed of multiple individual bets (legs).
    All legs must win for the parlay to win.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parlay_bets")
    
    # P.1 FIX: Increased max_digits to safely accommodate liabilities > $100,000.
    amount_wagered = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    
    # Total combined odds for the parlay (calculated from legs)
    combined_odds = models.CharField(
        max_length=20, help_text="Combined odds for the parlay (e.g., +250)", null=True
    )

    PARLAY_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("void", "Voided"),
    ]
    status = models.CharField(max_length=10, choices=PARLAY_STATUS_CHOICES, default="pending")
    
    # P.1 FIX: Increased max_digits to safely accommodate liabilities > $100,000.
    payout_amount = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Parlay Bets"

    def __str__(self):
        return f"Parlay by {self.user.username} ({self.amount_wagered})"
    
    def get_potential_payout(self) -> Decimal:
        """
        Calculates the potential payout, rounded to currency standard.
        """
        odds = self.get_combined_decimal_odds()

        if not odds:
             return Decimal("0.00")

        # P.3 FIX: Round the final payout to currency standard (2 decimal places)
        raw_payout = (self.amount_wagered or Decimal("0")) * odds
        return raw_payout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
    def get_combined_decimal_odds(self) -> Decimal:
        """
        Returns the product of decimal odds across all legs in the parlay.
        Delegates the odds conversion to the Bet model's decimal_odds property.
        """
        combined_odds = Decimal("1.00")

        for leg in self.legs.all(): 
            try:
                # P.2 FIX: Use the consistent decimal_odds property from the Bet model
                leg_decimal_odds = leg.decimal_odds
            except AttributeError:
                # Handle case where leg object might be missing the property (should not happen)
                return Decimal("0.00") 
                
            if leg_decimal_odds == Decimal("0.00"):
                # If odds are 0 (invalid odds_at_placement), return 0.00 to halt calculation
                return Decimal("0.00")

            combined_odds *= leg_decimal_odds
            
        # P.2 FIX: Return high-precision odds for use in the final payout calculation
        return combined_odds.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

# Note: User and other external models must be imported or accessible in the real file

class Bet(models.Model):
    """
    Represents a single bet placed by a user.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bets")
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name="bets", null=True, blank=True)
    
    # FIX: Increased max_digits to 15 and decimal_places to 4 for consistency and safety
    amount_wagered = models.DecimalField(max_digits=15, decimal_places=4, help_text="Amount user wagered", null=True)

    odds_at_placement = models.CharField(max_length=20, null=True, help_text="Odds user took (e.g., -110)")

    chosen_outcome = models.CharField(
        max_length=10,
        choices=[("over", "Over"), ("under", "Under")],
        help_text="Outcome chosen by the user for this bet",
        null=True,
    )

    BET_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("void", "Voided"),
    ]
    status = models.CharField(
        max_length=10, choices=BET_STATUS_CHOICES, default="pending"
    )
    override_used = models.BooleanField(default=False)
    override_notes = models.TextField(blank=True, null=True)
    
    # FIX: Increased max_digits to 15 and decimal_places to 4 for consistency and safety
    payout_amount = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )
    settled_at = models.DateTimeField(null=True, blank=True)

    is_parlay_leg = models.BooleanField(
        default=False, help_text="True if this bet is part of a parlay"
    )
    parlay_bet = models.ForeignKey(
        ParlayBet,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="legs",
    )
    is_placed = models.BooleanField(
        default=True, null=True, blank=True, help_text="True if the bet has been placed"
    )
    is_paid = models.BooleanField(
        default=False, null=True, blank=True, help_text="True if the bet has been paid"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Bets"

    def __str__(self):
        try:
            return f"Bet by {self.user.username} on {self.market.stock.symbol} ({self.amount_wagered})"
        except Exception:
            return f"Bet #{self.id}"

    # ------------------------------
    # ✅ Conversion Helpers
    # ------------------------------

    @property
    def decimal_odds(self) -> Decimal:
        """
        Converts American odds to Decimal odds (e.g. -110 -> 1.91, +150 -> 2.50)
        Uses high precision for internal parlay calculation accuracy.
        """
        try:
            odds = Decimal(self.odds_at_placement)
        except (TypeError, ValueError, InvalidOperation):
            return Decimal("0")

        if odds > 0:
            decimal_value = (odds / 100) + 1
        else:
            decimal_value = (Decimal("100") / abs(odds)) + 1

        # FIX: Increased precision to 8 decimal places for accurate compounding in ParlayBet
        return decimal_value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

    @property
    def fractional_odds(self) -> str:
        """
        Converts American odds to Fractional odds (e.g. -110 -> 10/11, +200 -> 2/1)
        """
        try:
            odds = Decimal(self.odds_at_placement)
        except (TypeError, ValueError, InvalidOperation):
            return "N/A"

        if odds > 0:
            numerator = odds
            denominator = Decimal("100")
        else:
            numerator = Decimal("100")
            denominator = abs(odds)

        # Reduce to simplest fraction
        num = int(numerator)
        den = int(denominator)
        common = gcd(num, den)

        simplified_num = num // common
        simplified_den = den // common

        return f"{simplified_num}/{simplified_den}"

    # ------------------------------
    # ✅ Potential payout
    # ------------------------------

    def get_potential_payout(self) -> Decimal:
        """
        Returns the potential payout (stake * decimal odds), rounded to currency standard.
        """
        raw_payout = (self.amount_wagered or Decimal("0")) * self.decimal_odds
        
        # FIX: Round the final payout to currency standard (2 decimal places)
        return raw_payout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def backfill_display_odds():
    for market in Market.objects.all():
        if not market.display_odds_over and market.implied_odds_over > 0:
            market.display_odds_over = implied_probability_to_american(market.implied_odds_over)

        if not market.display_odds_under and market.implied_odds_under > 0:
            market.display_odds_under = implied_probability_to_american(market.implied_odds_under)

        market.save()


# ===========================
# COMPETITION MODELS
# ===========================
class Competition(models.Model):
    """
    Represents a stock prediction competition/league where users can join
    and compete against each other over a specific time period.
    """
    
    COMPETITION_STATUS_CHOICES = [
        ("registration", "Registration Open"),  # Accepting new members
        ("active", "Active"),                    # Started, no new members
        ("completed", "Completed"),              # Finished, results final
        ("cancelled", "Cancelled"),              # Cancelled
    ]

    name = models.CharField(
        max_length=255,
        help_text="Name of the competition (e.g., 'Tech Stocks March Madness')"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the competition rules and format"
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_competitions",
        help_text="User who created this competition"
    )
    max_members = models.PositiveIntegerField(
        default=50,
        help_text="Maximum number of members allowed in this competition"
    )
    
    start_date = models.DateTimeField(
        help_text="When the competition starts (registration may close before this)"
    )
    end_date = models.DateTimeField(
        help_text="When the competition ends and leaderboard is finalized"
    )
    registration_close_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When registration closes (defaults to start_date if not set)"
    )
    
    status = models.CharField(
        max_length=15,
        choices=COMPETITION_STATUS_CHOICES,
        default="registration",
        help_text="Current status of the competition"
    )
    
    entry_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        null=True,
        blank=True,
        help_text="Entry fee in platform currency (0 for free)"
    )
    
    # Leaderboard & Rules
    scoring_method = models.CharField(
        max_length=50,
        default="net_profit",
        choices=[
            ("net_profit", "Net Profit/Loss"),
            ("roi", "Return on Investment (%)"),
            ("win_rate", "Win Rate (%)"),
            ("total_payout", "Total Payout Amount"),
        ],
        help_text="Method used to rank competitors on the leaderboard"
    )
    
    is_private = models.BooleanField(
        default=False,
        help_text="If True, only invited users can join"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Competitions"
        indexes = [
            models.Index(fields=["status", "start_date"]),
            models.Index(fields=["creator", "created_at"]),
        ]
    
    def __str__(self):
        return f"{self.name} (Ends: {self.end_date.strftime('%Y-%m-%d')})"
    
    @property
    def current_member_count(self):
        """Returns current number of active members in competition"""
        return self.members.filter(joined_at__isnull=False).count()
    
    @property
    def is_registration_open(self):
        """Check if registration is still open"""
        from django.utils import timezone
        now = timezone.now()
        close_date = self.registration_close_date or self.start_date
        return self.status == "registration" and now < close_date
    
    @property
    def is_active(self):
        """Check if competition is currently active"""
        from django.utils import timezone
        now = timezone.now()
        return self.status == "active" and now >= self.start_date and now <= self.end_date
    
    @property
    def is_full(self):
        """Check if competition has reached max members"""
        return self.current_member_count >= self.max_members
    
    def update_status(self):
        """
        Automatically updates competition status based on dates.
        Should be called periodically via a management command or signal.
        """
        from django.utils import timezone
        now = timezone.now()
        
        if self.status == "cancelled":
            return  # Don't change cancelled competitions
        
        if now >= self.end_date and self.status != "completed":
            self.status = "completed"
            self.save(update_fields=["status", "updated_at"])
        elif now >= self.start_date and self.status == "registration":
            self.status = "active"
            self.save(update_fields=["status", "updated_at"])


class CompetitionMember(models.Model):
    """
    Represents a user's membership in a competition.
    Tracks join date and final ranking.
    """
    
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="members"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="competition_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    
    # Final ranking (filled when competition ends)
    final_rank = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Final rank on competition leaderboard (1st, 2nd, etc.)"
    )
    final_score = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final score based on competition's scoring_method"
    )
    
    is_disqualified = models.BooleanField(
        default=False,
        help_text="If True, user is disqualified and won't appear on leaderboard"
    )
    
    class Meta:
        unique_together = ("competition", "user")
        ordering = ["-joined_at"]
        verbose_name_plural = "Competition Members"
        indexes = [
            models.Index(fields=["competition", "final_rank"]),
            models.Index(fields=["user", "competition"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.competition.name}"
    
    def get_member_stats(self):
        """
        Calculate member's stats for the competition period.
        Returns dict with profit/loss, win rate, bet count, etc.
        """
        from django.db.models import Count, Q, Sum
        
        # Get all bets placed by this user during competition period
        bets = Bet.objects.filter(
            user=self.user,
            created_at__gte=self.competition.start_date,
            created_at__lte=self.competition.end_date,
        )
        
        total_wagered = bets.aggregate(Sum("amount_wagered"))["amount_wagered__sum"] or Decimal("0")
        total_payout = bets.filter(status="won").aggregate(Sum("payout_amount"))["payout_amount__sum"] or Decimal("0")
        
        won_count = bets.filter(status="won").count()
        lost_count = bets.filter(status="lost").count()
        void_count = bets.filter(status="void").count()
        total_bets = bets.count()
        
        net_profit = total_payout - total_wagered
        win_rate = (won_count / total_bets * 100) if total_bets > 0 else Decimal("0")
        roi = (net_profit / total_wagered * 100) if total_wagered > 0 else Decimal("0")
        
        return {
            "total_bets": total_bets,
            "won": won_count,
            "lost": lost_count,
            "void": void_count,
            "total_wagered": round_two_places(total_wagered),
            "total_payout": round_two_places(total_payout),
            "net_profit": round_two_places(net_profit),
            "win_rate": round_two_places(win_rate),
            "roi": round_two_places(roi),
        }
    
    def calculate_score(self):
        """
        Calculate member's score based on competition's scoring_method.
        """
        stats = self.get_member_stats()
        
        scoring_method = self.competition.scoring_method
        
        if scoring_method == "net_profit":
            return Decimal(str(stats["net_profit"]))
        elif scoring_method == "roi":
            return Decimal(str(stats["roi"]))
        elif scoring_method == "win_rate":
            return Decimal(str(stats["win_rate"]))
        elif scoring_method == "total_payout":
            return Decimal(str(stats["total_payout"]))
        
        return Decimal("0.00")