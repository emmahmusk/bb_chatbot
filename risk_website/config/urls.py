from django.urls import path

from risk_site.views import LandingPageView, health_check


urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("health/", health_check, name="health"),
]
