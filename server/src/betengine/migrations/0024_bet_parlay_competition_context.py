from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("betengine", "0023_competition_starting_coin_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="bet",
            name="competition",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="competition_bets",
                to="betengine.competition",
            ),
        ),
        migrations.AddField(
            model_name="parlaybet",
            name="competition",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="competition_parlay_bets",
                to="betengine.competition",
            ),
        ),
    ]
