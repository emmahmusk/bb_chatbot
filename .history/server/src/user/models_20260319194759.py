from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum, Q
import math
from django.db.models.functions import Coalesce

# from user.utils import calculate_crs_risk_score

class PlatformSettings(models.Model):
    """
    Singleton model to store global exposure and profit settings for the platform.
    """
    base_exposure_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("500.00"))
    max_profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("15000.00"))
    max_crs = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("30.00"))
    minimum_stake = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("1.00"))
    max_risk_tolerance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("3000.00"), help_text="Default per-market maximum allowed net exposure.")
    global_max_risk_tolerance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("5000.00"), help_text="Global ceiling for market max risk tolerance.")
    starting_coin_balance = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("500.00"))

    def save(self, *args, **kwargs):
        """
        Ensure only one instance exists.
        """
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """
        Returns the singleton instance of PlatformSettings.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class Profile(models.Model):
    ODDS_CHOICES = [
        ('decimal', 'Decimal'),
        ('american', 'American'),
        ('fraction', 'Fraction'),
    ]

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    email_verified = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    current_address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    home_address = models.CharField(max_length=255, blank=True, null=True)
    tax_residency_country = models.CharField(max_length=20, blank=True, null=True)
    manual_kyc_required = models.BooleanField(default=False, null=True)
    crs_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.00"), verbose_name="BullBear CRS Multiplier")
    source_of_funds = models.TextField(blank=True, null=True)
    crs_risk_level = models.CharField(max_length=10, default="Low")
    betting_preference = models.CharField(max_length=10,choices=ODDS_CHOICES,default='decimal')
    city = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)

    max_stake = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    allowable_profit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.user.username
    def calculate_max_stake(self, decimal_odds: Decimal) -> Decimal:
        """
        Returns the maximum stake allowed for a specific market odds
        based on profit-driven CRS logic and global exposure limit.
        """
        if decimal_odds <= Decimal("1.00"):
            raise ValueError("Decimal odds must be greater than 1.00")

        settings = PlatformSettings.get_instance()
        max_profit = self.crs_risk_score * settings.base_exposure_limit
        self.allowable_profit = max_profit # Update allowable profit based on CRS risk score
        max_stake = max_profit / (decimal_odds - Decimal("1.00"))
        self.max_stake = max_stake # Update max stake
        self.save(update_fields=["allowable_profit", "max_stake"])

        return max_stake.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def user_kyc_upload_path(instance, filename):
    # This creates a path like: kyc/user_12/id_documents/passport.pdf
    return f"kyc/user_{instance.user.id}/id_documents/{filename}"


def user_selfie_upload_path(instance, filename):
    return f"kyc/user_{instance.user.id}/selfies/{filename}"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    coin_balance = models.DecimalField(max_digits=16, decimal_places=2, default=0.00)
    locked_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.balance}"


class Transaction(models.Model):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSACTION_TYPE = [
        (CREDIT, "Credit"),
        (DEBIT, "Debit"),
    ]

    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (SUCCESSFUL, "Successful"),
        (FAILED, "Failed"),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True, help_text="Status of the transaction")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return (f"{self.transaction_type.upper()}")


class KYCProfile(models.Model):
    """
    Stores KYC (Know Your Customer) information for users.
    It syncs with Profile/User data when created or updated to ensure consistency.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="kyc_profile")

    # ---- Basic Identification ----
    legal_first_name = models.CharField(max_length=100, null=True, blank=True)
    legal_last_name = models.CharField(max_length=100, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, null=True, blank=True)
    country_of_residence = models.CharField(max_length=100, null=True, blank=True)
    residential_address = models.TextField(null=True, blank=True)

    # ---- Additional CRS/KYC fields moved from Profile ----
    is_pep = models.BooleanField(default=False, null=True, help_text="Politically Exposed Person")
    has_multiple_citizenships = models.BooleanField(default=False, null=True)
    tax_residency_country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)

    # ---- Identification Documents ----
    id_document = models.FileField(upload_to=user_kyc_upload_path, null=True, blank=True)
    id_document_type = models.CharField(
        max_length=50,
        choices=[
            ("passport", "Passport"),
            ("national_id", "National ID"),
            ("driver_license", "Driver’s License"),
        ],
        default="passport",
    )
    id_verified = models.BooleanField(default=False)

    # ---- Employment & Source of Funds ----
    source_of_funds = models.TextField(blank=True, null=True)
    employment_status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("employed", "Employed"),
            ("self_employed", "Self-Employed"),
            ("student", "Student"),
            ("unemployed", "Unemployed"),
            ("retired", "Retired"),
        ],
    )
    employer_name = models.CharField(max_length=100, blank=True, null=True)
    employee_title = models.CharField(max_length=100, blank=True, null=True)

    # ---- Selfie / Face Verification ----
    selfie_image = models.ImageField(upload_to=user_selfie_upload_path, blank=True, null=True)

    # ---- KYC Process Metadata ----
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    kyc_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending",
    )
    reviewer_comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"KYCProfile for {self.user.username}"

    def populate_from_user_profile(self):
        """
        Auto-populate missing KYC fields from related User or Profile data.
        This ensures KYCProfile stays consistent with registration details.
        """
        user = self.user
        profile = getattr(user, "profile", None)

        # Fill name from user model
        if not self.legal_first_name and user.first_name:
            self.legal_first_name = user.first_name
        if not self.legal_last_name and user.last_name:
            self.legal_last_name = user.last_name

        # Pull additional details from Profile if available
        if profile:
            if not self.date_of_birth and profile.date_of_birth:
                self.date_of_birth = profile.date_of_birth
            if not self.city and profile.city:
                self.city = profile.city
            if not self.residential_address and profile.home_address:
                self.residential_address = profile.home_address
            if not self.postal_code and profile.postal_code:
                self.postal_code = profile.postal_code
            if not self.tax_residency_country and profile.tax_residency_country:
                self.tax_residency_country = profile.tax_residency_country
            if not self.source_of_funds and profile.source_of_funds:
                self.source_of_funds = profile.source_of_funds

    def save(self, *args, **kwargs):
        # Populate missing fields automatically before saving
        self.populate_from_user_profile()
        super().save(*args, **kwargs)

class CRSRiskAuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crs_audits")
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crs_changes_made",
    )
    previous_score = models.PositiveIntegerField(default=0)
    new_score = models.PositiveIntegerField(default=0)
    previous_level = models.CharField(max_length=10, null=True)
    new_level = models.CharField(max_length=10, null=True)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CRS Audit for {self.user.email} by {self.changed_by or 'System'}"


# user/models.py
