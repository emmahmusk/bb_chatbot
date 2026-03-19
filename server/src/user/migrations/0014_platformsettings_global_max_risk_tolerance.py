from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0013_platformsettings_starting_coin_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="global_max_risk_tolerance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("3000.00"),
                help_text="Global ceiling for market max risk tolerance.",
                max_digits=12,
            ),
        ),
    ]
