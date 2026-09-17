from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models
from .models import OpticOddsBetMonitor, SportsbookBetSlip


# Register your models here.
@admin.register(OpticOddsBetMonitor)
class OpticOddsBetMonitorAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event", "selection", "primary_sportsbook", "primary_decimal", "ev_odds", "ev_amount", "weighted_implied_probability")
    list_filter = ("primary_sportsbook", "sport", "league")
    search_fields = ("event", "fixture_id", "selection", "market")


@admin.register(SportsbookBetSlip)
class SportsbookBetSlipAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "leg_count", "stake", "combined_decimal_odds", "aggregate_comp_odds", "potential_payout", "ev_odds", "ev_amount", "status")
    list_filter = ("status",)
    search_fields = ("user__username",)
class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(
        choices=[("admin", "Admin"), ("superadmin", "Super Admin")], max_length=20
    )


# class AdminLog(models.Model):
#     admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True)
#     timestamp = models.DateTimeField(auto_now_add=True)
#     change_type = models.CharField(max_length=100)
#     before = models.JSONField()
#     after = models.JSONField()
