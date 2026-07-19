from django.urls import path
from .views import ChatView, ConversationDetailView, HealthView, MarketSyncView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("chat/", ChatView.as_view(), name="chat"),
    path("conversations/<uuid:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("markets/sync/", MarketSyncView.as_view(), name="market-sync"),
]
