from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="MarketDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("symbol", models.CharField(db_index=True, max_length=16)),
                ("company_name", models.CharField(blank=True, max_length=255)),
                ("expiry_date", models.DateField(blank=True, db_index=True, null=True)),
                ("content", models.TextField()),
                ("content_hash", models.CharField(max_length=64)),
                ("payload", models.JSONField(default=dict)),
                ("embedding", models.JSONField(default=list)),
                ("source_updated_at", models.DateTimeField(blank=True, null=True)),
                ("indexed_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["symbol", "expiry_date", "source_id"]},
        )
    ]
