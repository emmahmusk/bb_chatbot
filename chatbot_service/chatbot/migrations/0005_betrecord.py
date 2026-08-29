from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chatbot", "0004_betaudit_comparison_range")]

    operations = [
        migrations.CreateModel(
            name="BetRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fixture_id", models.CharField(blank=True, max_length=128)),
                ("event", models.CharField(blank=True, max_length=255)),
                ("sport", models.CharField(blank=True, max_length=64)),
                ("league", models.CharField(blank=True, max_length=128)),
                ("market", models.CharField(blank=True, max_length=128)),
                ("selection", models.CharField(blank=True, max_length=255)),
                ("sportsbook", models.CharField(max_length=128)),
                ("price", models.FloatField(blank=True, null=True)),
                ("decimal", models.FloatField(blank=True, null=True)),
                ("comparison_snapshot", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
