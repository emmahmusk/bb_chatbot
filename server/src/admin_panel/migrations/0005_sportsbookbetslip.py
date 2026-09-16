from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("admin_panel", "0004_opticoddsbetmonitor"),
    ]

    operations = [
        migrations.CreateModel(
            name="SportsbookBetSlip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stake", models.DecimalField(decimal_places=2, max_digits=14)),
                ("combined_decimal_odds", models.DecimalField(decimal_places=8, max_digits=18)),
                ("potential_payout", models.DecimalField(decimal_places=2, max_digits=18)),
                ("leg_count", models.PositiveIntegerField(default=1)),
                ("status", models.CharField(default="recorded", max_length=20)),
                ("legs", models.JSONField(default=list)),
                ("comparison_notes", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sportsbook_betslips", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
