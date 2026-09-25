from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_panel", "0008_sportsbook_parlay_aggregate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="opticoddsbetmonitor",
            name="primary_sportsbook",
            field=models.CharField(default="hardrockbet", max_length=80),
        ),
    ]
