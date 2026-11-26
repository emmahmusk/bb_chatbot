from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("admin_panel", "0011_demooddsoverride")]
    operations = [migrations.CreateModel(
        name="SportsbookComparisonSettings",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("selected_books", models.JSONField(default=list)),
            ("provider_weights", models.JSONField(default=dict)),
            ("updated_at", models.DateTimeField(auto_now=True)),
        ],
    )]
