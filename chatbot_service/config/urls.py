from django.urls import include, path
from chatbot.views import ChatPageView
from chatbot.views import OddsComparisonPageView

urlpatterns = [
    path("", ChatPageView.as_view(), name="chat-page"),
    path("odds-comparison/", OddsComparisonPageView.as_view(), name="odds-comparison-page"),
    path("api/", include("chatbot.urls")),
]
