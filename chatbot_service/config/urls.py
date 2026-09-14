from django.urls import include, path
from chatbot.views import ChatPageView
from chatbot.views import OddsComparisonPageView, AdminSportsbookPageView, AdminMonitorPageView

urlpatterns = [
    path("", ChatPageView.as_view(), name="chat-page"),
    path("odds-comparison/", OddsComparisonPageView.as_view(), name="odds-comparison-page"),
    path("sportsbook/", AdminSportsbookPageView.as_view(), name="admin-sportsbook-page"),
    path("sportsbook/monitor/", AdminMonitorPageView.as_view(), name="admin-monitor-page"),
    path("api/", include("chatbot.urls")),
]
