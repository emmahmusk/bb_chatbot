from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chatbot", "0003_betaudit")]

    operations = [
        migrations.AddField(model_name="betaudit", name="lowest_sportsbook", field=models.CharField(blank=True, max_length=128)),
        migrations.AddField(model_name="betaudit", name="lowest_decimal", field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name="betaudit", name="spread_decimal", field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name="betaudit", name="audit_reason", field=models.CharField(blank=True, max_length=255)),
    ]
