from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_panel", "0005_sportsbookbetslip"),
    ]

    operations = [
        migrations.AddField(
            model_name="opticoddsbetmonitor",
            name="aggregate_comp_odds",
            field=models.FloatField(blank=True, help_text="Average peer implied probability: mean(1 / peer decimal odds).", null=True),
        ),
        migrations.AddField(
            model_name="opticoddsbetmonitor",
            name="ev_amount",
            field=models.DecimalField(blank=True, decimal_places=2, help_text="Cash EV using the configured EV amount formula.", max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="opticoddsbetmonitor",
            name="ev_odds",
            field=models.FloatField(blank=True, help_text="Baseline implied probability minus aggregate peer implied probability.", null=True),
        ),
        migrations.AddField(
            model_name="sportsbookbetslip",
            name="ev_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="sportsbookbetslip",
            name="ev_odds",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sportsbookbetslip",
            name="leg_aggregate_comp_odds",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
