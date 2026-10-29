from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chatbot", "0007_sportsbookpreference_provider_weights")]

    operations = [
        migrations.CreateModel(
            name="DemoOddsLabOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fixture_id", models.CharField(max_length=128)),
                ("sportsbook", models.CharField(max_length=128)),
                ("market", models.CharField(default="moneyline", max_length=128)),
                ("selection", models.CharField(max_length=255)),
                ("decimal_odds", models.FloatField()),
                ("american_price", models.IntegerField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["sportsbook", "selection"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("fixture_id", "sportsbook", "market", "selection"),
                        name="chatbot_demo_odds_unique_line",
                    )
                ],
            },
        )
    ]
