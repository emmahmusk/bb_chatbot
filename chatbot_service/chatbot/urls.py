from django.urls import path
from .views import ChatView, ConversationDetailView, HealthView, MarketSyncView
from .optic_odds_views import OpticCatalogView, OpticOddsCompareView, OpticSportsbooksView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("chat/", ChatView.as_view(), name="chat"),
    path("conversations/<uuid:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("markets/sync/", MarketSyncView.as_view(), name="market-sync"),
    path("odds/providers/", OpticSportsbooksView.as_view(), name="optic-odds-providers"),
    path("odds/catalog/", OpticCatalogView.as_view(), name="optic-odds-catalog"),
    path("odds/compare/", OpticOddsCompareView.as_view(), name="optic-odds-compare"),
]
