from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0012_wallet_coin_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="starting_coin_balance",
            field=models.DecimalField(decimal_places=2, default=Decimal("500.00"), max_digits=16),
        ),
    ]
