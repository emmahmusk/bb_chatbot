from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("admin_panel", "0006_sportsbook_ev_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="opticoddsbetmonitor",
            name="sportsbook_slip",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="monitored_legs", to="admin_panel.sportsbookbetslip"),
        ),
    ]
