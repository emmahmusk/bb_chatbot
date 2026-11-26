"""One source of truth for the Flutter monitor and sportsbook comparisons."""
import math
from django.conf import settings
from admin_panel.models import SportsbookComparisonSettings


def baseline():
    return str(getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK", "draftkings") or "draftkings").strip().lower()


def normalize_weights(books, supplied=None):
    supplied = supplied if isinstance(supplied, dict) else {}
    weights = {}
    for book in books:
        try:
            value = float(supplied.get(book, 0))
        except (TypeError, ValueError):
            value = 0
        weights[book] = value if math.isfinite(value) and value > 0 else 0
    total = sum(weights.values())
    return {book: value / total for book, value in weights.items()} if total else {book: 1 / len(books) for book in books}


def saved_preference():
    return SportsbookComparisonSettings.objects.filter(pk=1).first()


def preference_payload(preference=None):
    primary = baseline()
    configured = getattr(settings, "OPTIC_ODDS_COMPARISON_SPORTSBOOKS", [])
    books = preference.selected_books if preference else configured
    peers = list(dict.fromkeys(str(book).strip().lower() for book in books if str(book).strip().lower() != primary and str(book).strip()))[:4]
    peers = peers or [book for book in ["fanduel", "pinnacle", "bet365"] if book != primary]
    return {
        "baseline": primary,
        "baseline_label": getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK_LABEL", "DraftKings"),
        "selected_books": peers,
        "provider_weights": normalize_weights(peers, preference.provider_weights if preference else None),
    }
