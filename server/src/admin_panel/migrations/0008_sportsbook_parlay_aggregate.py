from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_panel", "0007_monitor_sportsbook_slip"),
    ]

    operations = [
        migrations.AddField(
            model_name="sportsbookbetslip",
            name="aggregate_comp_odds",
            field=models.FloatField(
                blank=True,
                help_text="Average reciprocal of each comparison provider's combined parlay odds.",
                null=True,
            ),
        ),
    ]
