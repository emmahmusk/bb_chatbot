from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chatbot", "0005_betrecord")]

    operations = [
        migrations.CreateModel(
            name="SportsbookPreference",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("selected_books", models.JSONField(blank=True, default=list)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
    ]
