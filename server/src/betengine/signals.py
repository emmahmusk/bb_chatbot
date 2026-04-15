# In betengine/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task
from .models import Bet, ParlayBet
from user.models import Profile
# from user.tasks import recalculate_user_crs_exposure


@receiver(post_save, sender=Bet)
def enqueue_crs_update_on_bet_save(sender, instance, **kwargs):
    if instance.user and instance.status in ['pending', 'won', 'lost', 'void']:
        profile, _ = Profile.objects.get_or_create(user=instance.user)
        if instance.decimal_odds > 1.00:
            async_task(profile.calculate_max_stake, instance.decimal_odds)

@receiver(post_save, sender=ParlayBet)
def enqueue_crs_update_on_parlay_save(sender, instance, **kwargs):
    if instance.user and instance.status in ['pending', 'won', 'lost', 'void']:
        profile, _ = Profile.objects.get_or_create(user=instance.user)
        decimal_odds = instance.get_combined_decimal_odds()
        if decimal_odds > 1.00:
            async_task(profile.calculate_max_stake, decimal_odds)