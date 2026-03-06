from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0011_platformsettings_max_risk_tolerance"),
    ]

    operations = [
        migrations.AddField(
            model_name="wallet",
            name="coin_balance",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=16),
        ),
    ]
