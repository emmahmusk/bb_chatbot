from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chatbot", "0006_sportsbookpreference")]

    operations = [
        migrations.AddField(
            model_name="sportsbookpreference",
            name="provider_weights",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
