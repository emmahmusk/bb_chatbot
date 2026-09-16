# Create your models here.

# from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.db import models
from user.models import Profile
from betengine.models import Bet, Stock, Market
# from django.contrib.auth.models import AbstractUser

User = get_user_model()


class AdminUserRole(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("superadmin", "Super Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_by = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name="role_assigned_by"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class CRSModificationLog(models.Model):
    """
    Logs changes made to a user's Customer Risk Score by an admin.
    """

    admin_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="crs_modifications",
        help_text="The admin user who adjusted the CRS.",
    )
    user_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,  # If user profile is deleted, its CRS logs should also be deleted
        related_name="crs_logs",
        help_text="The user profile whose CRS was modified.",
    )
    old_crs = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Original CRS value."
    )
    new_crs = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="New CRS value."
    )
    reason = models.TextField(
        blank=True, null=True, help_text="Reason for CRS adjustment."
    )
    modified_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp of the modification."
    )

    class Meta:
        ordering = ["-modified_at"]
        verbose_name = "CRS Modification Log"
        verbose_name_plural = "CRS Modification Logs"

    def __str__(self):
        admin_info = self.admin_user.username if self.admin_user else "Deleted Admin"
        return f"CRS for {self.user_profile.user.username} adjusted by {admin_info} to {self.new_crs}"


class BetOverrideLog(models.Model):
    """
    Logs manual overrides to a bet's status or payout by an admin.
    """

    admin_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="bet_overrides"
    )
    bet = models.ForeignKey(Bet, on_delete=models.CASCADE, related_name="override_logs")
    old_status = models.CharField(max_length=10, choices=Bet.BET_STATUS_CHOICES)
    new_status = models.CharField(max_length=10, choices=Bet.BET_STATUS_CHOICES)
    old_payout_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    new_payout_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    reason = models.TextField(blank=True, null=True)
    overridden_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-overridden_at"]
        verbose_name = "Bet Override Log"
        verbose_name_plural = "Bet Override Logs"

    def __str__(self):
        admin_info = self.admin_user.username if self.admin_user else "System"
        return f"Bet {self.bet.id} overridden by {admin_info} from {self.old_status} to {self.new_status}"


class OddsAdjustmentLog(models.Model):
    """
    Logs changes made to market display odds by an admin.
    """

    admin_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # If admin user is deleted, log entry remains, but admin_user becomes NULL
        null=True,
        related_name="odds_adjustments",
        help_text="The admin user who performed the odds adjustment.",
    )
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name="odds_logs",
        help_text="The market for which odds were adjusted.",
    )
    old_display_odds_over = models.CharField(max_length=20, null=True, blank=True)
    old_display_odds_under = models.CharField(max_length=20, null=True, blank=True)
    new_display_odds_over = models.CharField(max_length=20, null=True, blank=True)
    new_display_odds_under = models.CharField(max_length=20, null=True, blank=True)
    adjusted_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp of the adjustment."
    )

    class Meta:
        ordering = ["-adjusted_at"]
        verbose_name = "Odds Adjustment Log"
        verbose_name_plural = "Odds Adjustment Logs"

    def __str__(self):
        # Added a check for admin_user being None in case it's set_null
        admin_info = self.admin_user.username if self.admin_user else "Deleted Admin"
        return f"Odds adjustment for Market {self.market.id} by {admin_info} at {self.adjusted_at.strftime('%Y-%m-%d %H:%M')}"


class TickerControl(models.Model):
    ticker = models.CharField(max_length=10)
    is_enabled = models.BooleanField(default=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticker} - {'Enabled' if self.is_enabled else 'Disabled'}"


class LiabilitySnapshot(models.Model):
    ticker = models.CharField(max_length=10)
    expiry_date = models.DateField()
    strike_price = models.FloatField()
    option_type = models.CharField(
        max_length=10, choices=[("call", "Call"), ("put", "Put")]
    )
    total_liability = models.DecimalField(max_digits=12, decimal_places=2)
    snapshot_time = models.DateTimeField(auto_now_add=True)


class KPIMetrics(models.Model):
    date = models.DateField()
    total_bets = models.IntegerField()
    total_payouts = models.DecimalField(max_digits=12, decimal_places=2)
    total_volume = models.DecimalField(max_digits=12, decimal_places=2)
    top_winners = models.JSONField()  # [{"user_id": 1, "profit": 500}, ...]
    top_losers = models.JSONField()  # [{"user_id": 2, "loss": -300}, ...]
    created_at = models.DateTimeField(auto_now_add=True)


class AdminActionLog(models.Model):
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=100)
    before_value = models.TextField(null=True, blank=True)
    after_value = models.TextField(null=True, blank=True)
    target_model = models.CharField(max_length=100, null=True)
    target_id = models.IntegerField(null=True, blank=True)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


# If not already in user/models.py
class KYC(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    document_url = models.URLField()
    address_proof_url = models.URLField()
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"KYC({self.user.username}): {self.status}"


class MarketNudgeHistory(models.Model):
    """
    Records every odds nudge action for auditing and analytics.
    Helps track human interventions on auto-generated odds.
    """

    DIRECTION_CHOICES = [(1, "Up (+1)"),(-1, "Down (-1)"),]

    SIDE_CHOICES = [
        ("over", "Over"),
        ("under", "Under"),
    ]

    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name="nudge_history", help_text="The specific market whose odds were nudged.",)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="nudge_history", help_text="The stock this market belongs to.",)

    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    direction = models.SmallIntegerField(choices=DIRECTION_CHOICES)

    previous_display_odds = models.CharField(max_length=20, help_text="Display odds before the nudge (e.g. American odds).", null=True)
    new_display_odds = models.CharField(max_length=20, help_text="Display odds after the nudge (e.g. American odds).", null=True)

    previous_br_true_percent = models.DecimalField(max_digits=8, decimal_places=4, help_text="BR true percent before nudge (e.g. 51.23).", null=True)
    new_br_true_percent = models.DecimalField(max_digits=8, decimal_places=4, help_text="BR true percent after nudge (e.g. 52.11).", null=True)
    applied_offset = models.DecimalField(max_digits=8, decimal_places=4, default=0.0, help_text="Cumulative offset from base feed (total applied nudges).", null=True)

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="market_nudges",
        help_text="Admin or system user who performed the nudge.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, help_text="Optional contextual note or explanation for the nudge.", null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Market Nudge History"
        verbose_name_plural = "Market Nudge Histories"

    def __str__(self):
        return (
            f"{self.stock.symbol} | {self.market.target_price} | "
            f"{self.side.upper()} {self.get_direction_display()} to {self.new_display_odds}"
        )

    @classmethod
    def record_nudge(
        cls,
        market,
        side,
        direction,
        prev_display_odds,
        new_display_odds,
        prev_percent,
        new_percent,
        user=None,
        note="",
        applied_offset=0.0):
        """
        Safely record a nudge operation.
        """
        return cls.objects.create(
            market=market,
            stock=market.stock,
            side=side,
            direction=direction,
            previous_display_odds=prev_display_odds,
            new_display_odds=new_display_odds,
            previous_br_true_percent=prev_percent,
            new_br_true_percent=new_percent,
            created_by=user,
            note=note,
            applied_offset=applied_offset,
        )

class WithdrawalRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    requested_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False)


class OpticOddsBetMonitor(models.Model):
    """Immutable sportsbook bet snapshot for the admin odds-audit POC."""

    admin_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="optic_odds_bets")
    fixture_id = models.CharField(max_length=128)
    event = models.CharField(max_length=255, blank=True)
    sport = models.CharField(max_length=80, blank=True)
    league = models.CharField(max_length=120, blank=True)
    market = models.CharField(max_length=120)
    selection = models.CharField(max_length=255)
    primary_sportsbook = models.CharField(max_length=80, default="draftkings")
    primary_price = models.CharField(max_length=40, blank=True)
    primary_decimal = models.FloatField(null=True, blank=True)
    stake = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    provider_odds = models.JSONField(default=dict)
    provider_weights = models.JSONField(default=dict)
    weighted_implied_probability = models.FloatField(null=True, blank=True)
    fair_decimal = models.FloatField(null=True, blank=True)
    aggregate_comp_odds = models.FloatField(null=True, blank=True, help_text="Average peer implied probability: mean(1 / peer decimal odds).")
    ev_odds = models.FloatField(null=True, blank=True, help_text="Baseline implied probability minus aggregate peer implied probability.")
    ev_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Cash EV using the configured EV amount formula.")
    is_potentially_bad = models.BooleanField(default=False)
    audit_reason = models.CharField(max_length=255, blank=True)
    edge_decimal = models.FloatField(null=True, blank=True)
    note = models.TextField()
    odds_snapshot = models.JSONField(default=list)
    sportsbook_slip = models.ForeignKey("SportsbookBetSlip", null=True, blank=True, on_delete=models.SET_NULL, related_name="monitored_legs")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event or self.fixture_id} | {self.selection} | {self.created_at:%Y-%m-%d %H:%M}"


class SportsbookBetSlip(models.Model):
    """A sports betslip snapshot recorded from the OpticOdds sportsbook POC."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sportsbook_betslips")
    stake = models.DecimalField(max_digits=14, decimal_places=2)
    combined_decimal_odds = models.DecimalField(max_digits=18, decimal_places=8)
    potential_payout = models.DecimalField(max_digits=18, decimal_places=2)
    ev_odds = models.FloatField(null=True, blank=True)
    ev_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    leg_aggregate_comp_odds = models.JSONField(default=list, blank=True)
    leg_count = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, default="recorded")
    legs = models.JSONField(default=list)
    comparison_notes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sportsbook slip #{self.pk} · {self.leg_count} leg(s)"
