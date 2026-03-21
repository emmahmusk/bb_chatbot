from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0014_platformsettings_global_max_risk_tolerance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="platformsettings",
            name="global_max_risk_tolerance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("5000.00"),
                help_text="Global ceiling for market max risk tolerance.",
                max_digits=12,
            ),
        ),
    ]
