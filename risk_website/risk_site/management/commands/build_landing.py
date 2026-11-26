from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = "Render the Django landing template and collect its static assets for S3/CloudFront."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="dist", help="Directory receiving the static site.")

    def handle(self, *args, **options):
        output = Path(options["output"]).resolve()
        output.mkdir(parents=True, exist_ok=True)
        static_root = output / "static"
        static_root.mkdir(parents=True, exist_ok=True)
        settings.STATIC_ROOT = static_root
        try:
            call_command("collectstatic", interactive=False, verbosity=0, clear=True)
            html = render_to_string(
                "risk_site/index.html",
                {
                    "contact_email": settings.CONTACT_EMAIL,
                },
                request=None,
            )
            # Keep the Django template canonical with /static/ URLs, but make
            # the exported S3 artifact portable when opened from a local dist
            # folder during review.
            html = html.replace('="/static/', '="static/')
        except Exception as exc:  # pragma: no cover - command-line failure message
            raise CommandError(f"Unable to build the risk landing page: {exc}") from exc
        (output / "index.html").write_text(html, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Risk landing page built at {output}"))
