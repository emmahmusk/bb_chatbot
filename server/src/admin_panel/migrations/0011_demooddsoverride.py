from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("admin_panel", "0010_draftkings_baseline")]

    operations = [
        migrations.CreateModel(
            name="DemoOddsOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fixture_id", models.CharField(max_length=128)),
                ("sportsbook", models.CharField(max_length=80)),
                ("market", models.CharField(default="moneyline", max_length=120)),
                ("selection", models.CharField(max_length=255)),
                ("decimal_odds", models.DecimalField(decimal_places=4, max_digits=10)),
                ("american_price", models.IntegerField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="demo_odds_overrides", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["sportsbook", "selection"]},
        ),
        migrations.AddConstraint(
            model_name="demooddsoverride",
            constraint=models.UniqueConstraint(fields=("fixture_id", "sportsbook", "market", "selection"), name="unique_demo_odds_override"),
        ),
    ]
