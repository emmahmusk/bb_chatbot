from django.urls import include, path
from betengine.sportsbook_api import SportsbookRecordBetSlipView

urlpatterns = [
    path("admin_panel/", include("admin_panel.urls")),
    path("bet/sportsbook/betslips/", SportsbookRecordBetSlipView.as_view()),
]
