from django.urls import include, path
from chatbot.views import ChatPageView

urlpatterns = [
    path("", ChatPageView.as_view(), name="chat-page"),
    path("api/", include("chatbot.urls")),
]
