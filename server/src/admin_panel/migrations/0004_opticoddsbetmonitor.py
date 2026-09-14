from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("admin_panel", "0003_alter_marketnudgehistory_applied_offset_and_more")]

    operations = [migrations.CreateModel(
        name="OpticOddsBetMonitor",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("fixture_id", models.CharField(max_length=128)),
            ("event", models.CharField(blank=True, max_length=255)),
            ("sport", models.CharField(blank=True, max_length=80)),
            ("league", models.CharField(blank=True, max_length=120)),
            ("market", models.CharField(max_length=120)),
            ("selection", models.CharField(max_length=255)),
            ("primary_sportsbook", models.CharField(default="draftkings", max_length=80)),
            ("primary_price", models.CharField(blank=True, max_length=40)),
            ("primary_decimal", models.FloatField(blank=True, null=True)),
            ("stake", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
            ("provider_odds", models.JSONField(default=dict)),
            ("provider_weights", models.JSONField(default=dict)),
            ("weighted_implied_probability", models.FloatField(blank=True, null=True)),
            ("fair_decimal", models.FloatField(blank=True, null=True)),
            ("is_potentially_bad", models.BooleanField(default=False)),
            ("audit_reason", models.CharField(blank=True, max_length=255)),
            ("edge_decimal", models.FloatField(blank=True, null=True)),
            ("note", models.TextField()),
            ("odds_snapshot", models.JSONField(default=list)),
            ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ("admin_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="optic_odds_bets", to=settings.AUTH_USER_MODEL)),
        ],
        options={"ordering": ["-created_at"]},
    )]
