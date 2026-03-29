from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from user.models import CompetitionMember


class Command(BaseCommand):
    help = (
        "Backfill CompetitionMember.competition_coin_balance for memberships "
        "that still have 0.00, using each competition's starting_coin_balance. "
        "Runs in dry-run mode unless --apply is provided."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply database updates. Without this flag, command runs as dry-run.",
        )
        parser.add_argument(
            "--competition-id",
            type=int,
            help="Limit backfill to a single competition id.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        competition_id = options.get("competition_id")

        queryset = CompetitionMember.objects.select_related("competition").filter(
            competition_coin_balance=Decimal("0.00"),
            competition__starting_coin_balance__gt=Decimal("0.00"),
        )

        if competition_id is not None:
            queryset = queryset.filter(competition_id=competition_id)

        candidates = list(queryset)

        if not candidates:
            self.stdout.write(
                self.style.SUCCESS("No memberships require backfill.")
            )
            return

        self.stdout.write(
            f"Found {len(candidates)} membership(s) with 0.00 competition balance "
            f"and positive competition starting balance."
        )

        preview_limit = 10
        for member in candidates[:preview_limit]:
            self.stdout.write(
                "- member_id={member_id}, competition_id={competition_id}, "
                "user_id={user_id}, current={current}, target={target}".format(
                    member_id=member.id,
                    competition_id=member.competition_id,
                    user_id=member.user_id,
                    current=member.competition_coin_balance,
                    target=member.competition.starting_coin_balance,
                )
            )

        if len(candidates) > preview_limit:
            self.stdout.write(
                f"...and {len(candidates) - preview_limit} more."
            )

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run complete. Re-run with --apply to persist changes."
                )
            )
            return

        updated_count = 0
        with transaction.atomic():
            for member in candidates:
                member.competition_coin_balance = member.competition.starting_coin_balance
                member.save(update_fields=["competition_coin_balance"])
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete. Updated {updated_count} membership(s)."
            )
        )
