from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile
from .wallet_utils import get_or_create_wallet_with_starting_coins

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_user_profile_and_wallet(sender, instance, created, **kwargs):
    """
    Keep core user relations present for both new and legacy users.

    Some existing rows were created without a Profile, and the login/profile
    endpoints assume the one-to-one relation exists. This signal makes user
    creation idempotent and safe going forward.
    """
    Profile.objects.get_or_create(user=instance)

    if created:
        get_or_create_wallet_with_starting_coins(user=instance)
