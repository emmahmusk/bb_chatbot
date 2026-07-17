from django.urls import path
from .views import ChatView, HealthView, MarketSyncView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("chat/", ChatView.as_view(), name="chat"),
    path("markets/sync/", MarketSyncView.as_view(), name="market-sync"),
]
