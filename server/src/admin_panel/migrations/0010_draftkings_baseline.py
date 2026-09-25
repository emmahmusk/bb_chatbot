from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_panel", "0009_hardrock_baseline"),
    ]

    operations = [
        migrations.AlterField(
            model_name="opticoddsbetmonitor",
            name="primary_sportsbook",
            field=models.CharField(default="draftkings", max_length=80),
        ),
    ]
