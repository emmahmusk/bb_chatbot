"""Server-side proxy for the admin OpticOdds POC hosted on the EC2 API."""
import requests
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SportsbookPreference


BASELINE_SPORTSBOOK = "draftkings"
DEFAULT_COMPARISON_BOOKS = ["fanduel", "pinnacle", "bet365"]


def _server_request(request, path, method="get", payload=None):
    base = getattr(settings, "ADMIN_SERVER_BASE_URL", "").rstrip("/")
    # Accept either the shared API host or a value that already includes the
    # admin prefix, without ever producing /admin_panel/admin_panel/...
    if base.endswith("/admin_panel"):
        base = base[:-len("/admin_panel")].rstrip("/")
    if not base:
        return Response({"detail": "ADMIN_SERVER_BASE_URL is not configured."}, status=503)
    service_key = str(getattr(settings, "ADMIN_SERVER_API_KEY", "") or "").strip()
    # Preserve the logged-in user's JWT for bet placement. The deployment JWT
    # remains a fallback for the admin-only proxy screens.
    token = request.headers.get("Authorization", "") or getattr(settings, "ADMIN_SERVER_JWT", "")
    if token and not token.lower().startswith("bearer "):
        token = f"Bearer {token}"
    headers = {"Accept": "application/json"}
    if service_key:
        headers["X-Admin-API-Key"] = service_key
    if token:
        headers["Authorization"] = token
    try:
        response = requests.request(
            method,
            f"{base}/{path.lstrip('/')}",
            params=request.query_params,
            json=payload,
            headers=headers,
            timeout=getattr(settings, "ADMIN_SERVER_TIMEOUT_SECONDS", 15),
        )
        try:
            body = response.json()
        except ValueError:
            body = {"detail": response.text or "The admin server returned an invalid response."}
        proxied = Response(body, status=response.status_code)
        proxied["Cache-Control"] = "no-store, max-age=0"
        return proxied
    except requests.RequestException:
        return Response({"detail": "The admin sportsbook server is unavailable."}, status=status.HTTP_502_BAD_GATEWAY)


def _proxy(request, path, method="get", payload=None):
    return _server_request(request, f"admin_panel/optic-odds/{path.lstrip('/')}", method=method, payload=payload)


class AdminSportsbookProxyView(APIView):
    def get(self, request, resource="sports"):
        return _proxy(request, resource)

    def post(self, request):
        return _proxy(request, "bets/", method="post", payload=request.data)


class AdminSportsbookBetSlipView(APIView):
    """Forward a user betslip using the books saved in the monitor settings.

    The Flutter sportsbook only sends DraftKings prices to the user interface.
    This server-side bridge adds the monitor's saved comparison books before
    forwarding the authenticated betslip to the EC2 API, so peer prices never
    need to be exposed in the betting UI.
    """

    def post(self, request):
        if not request.headers.get("Authorization"):
            return Response({"detail": "Log in before placing a sportsbook bet."}, status=status.HTTP_401_UNAUTHORIZED)
        preference = SportsbookPreference.objects.filter(pk=1).first()
        selected = preference.selected_books if preference else DEFAULT_COMPARISON_BOOKS
        books = list(dict.fromkeys([BASELINE_SPORTSBOOK, *[str(book).strip().lower() for book in selected if str(book).strip()]]))[:5]
        payload = dict(request.data)
        payload["sportsbooks"] = books
        return _server_request(request, "bet/sportsbook/betslips/", method="post", payload=payload)


class AdminMonitorProxyView(APIView):
    def get(self, request):
        return _proxy(request, "bets/monitor/")


class AdminSportsbookSettingsView(APIView):
    """Persist the shared comparison-book selection for the admin POC."""

    def get(self, request):
        preference = SportsbookPreference.objects.filter(pk=1).first()
        selected = preference.selected_books if preference else DEFAULT_COMPARISON_BOOKS
        return Response({"baseline": BASELINE_SPORTSBOOK, "selected_books": selected})

    def post(self, request):
        selected = request.data.get("selected_books")
        if not isinstance(selected, list):
            return Response({"detail": "selected_books must be a list."}, status=status.HTTP_400_BAD_REQUEST)
        selected = list(dict.fromkeys(str(book).strip().lower() for book in selected if str(book).strip()))
        selected = [book for book in selected if book != BASELINE_SPORTSBOOK][:4]
        if not selected:
            return Response({"detail": "Select at least one comparison book."}, status=status.HTTP_400_BAD_REQUEST)
        preference, _ = SportsbookPreference.objects.update_or_create(
            pk=1,
            defaults={"selected_books": selected},
        )
        return Response({"baseline": BASELINE_SPORTSBOOK, "selected_books": preference.selected_books, "saved": True})
