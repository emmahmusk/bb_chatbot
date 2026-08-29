from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chatbot", "0002_conversation_chatmessage")]

    operations = [
        migrations.CreateModel(
            name="BetAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fixture_id", models.CharField(blank=True, max_length=128)),
                ("sport", models.CharField(blank=True, max_length=64)),
                ("league", models.CharField(blank=True, max_length=128)),
                ("market", models.CharField(blank=True, max_length=128)),
                ("selection", models.CharField(blank=True, max_length=255)),
                ("chosen_sportsbook", models.CharField(max_length=128)),
                ("chosen_price", models.FloatField(blank=True, null=True)),
                ("chosen_decimal", models.FloatField(blank=True, null=True)),
                ("best_sportsbook", models.CharField(blank=True, max_length=128)),
                ("best_price", models.FloatField(blank=True, null=True)),
                ("best_decimal", models.FloatField(blank=True, null=True)),
                ("edge_decimal", models.FloatField(blank=True, null=True)),
                ("is_bad_bet", models.BooleanField(db_index=True, default=False)),
                ("comparison_snapshot", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
