# user/signals.py
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from django_q.tasks import async_task
from .models import Wallet, Profile

User = get_user_model()

@receiver(post_save, sender=User)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_or_initialize_user_profile(sender, instance, created, **kwargs):
    """
    Ensures a Profile exists for every user.
    If it already exists, we just leave it as is.
    Initializes cached fields safely for new users.
    """
    profile, created_profile = Profile.objects.get_or_create(
        user=instance,
        defaults={
            "total_wagered": Decimal("0.00"),
            "raw_crs": Decimal("0.00"),
            "normalized_crs": Decimal("0.00"),
            "allowable_payout": Profile.base_payout,
            "risk_tier": "Bronze",
        }
    )

    # Use the instance method instead of the old standalone function
    async_task(profile.recalculate_crs)

# @receiver(post_save, sender=Profile)
# def update_crs_risk_score(sender, instance, **kwargs):
#     instance.update_crs_risk()
