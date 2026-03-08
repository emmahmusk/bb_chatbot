from django.urls import path

from admin_panel.views.kyc import (
    CRSRiskAuditLogView,
    CRSRiskScoreView,
    ManualKYCTriggerView
)
from admin_panel.views.vig import BulkOverrideVigByIdsView, OverrideVigView
from admin_panel.views.market import MarketOddsResetView, MarketOddsNudgeView, StockListView, StockToggleUpdateView, StockRefreshView, GroupedMarketView, MarketStatusUpdateAPIView, SuspendedMarketsView, SuspendedMarketDetailView, StockSettlementDetailView
from admin_panel.views.users import AlphaVantageVolumeView, BetVolumeAdminView, AdminBetSettlementView
from admin_panel.api import AdminMarketOverrideAPIView, UpdateUserCRSView, UpdatePlatformSettingsView, AnalyticsDashboardAPIView, AnalyticsUserDashboardAPIView, AdminAnalyticsAPIView, DeleteExpiringMarketsView, KYCFileReviewListAPIView, TotalGGRAPIView, AdminSettleBetView, AdminUserListView, SignupAPIView, LoginAPIView, AdminBetFeedView, AdminKYCViewSet, AdminUserListAPIView, AnalyticsDashboardAPIViewNew

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="login"),
    path("signup/", SignupAPIView.as_view(), name="signup"),
    path('user_list/', AdminUserListView.as_view(), name='user_list'),
    path("kyc-files/", KYCFileReviewListAPIView.as_view(), name="admin-kyc-files"),
    path('bet_feed/', AdminBetFeedView.as_view(), name='bet_feed'),
    path("user-bets/", AdminUserListAPIView.as_view(), name="admin_user_bets"),
    path("bets/<int:bet_id>/settle/", AdminSettleBetView.as_view(), name="admin-settle-bet"),
    path("market/set-vig/", OverrideVigView.as_view(), name="market-set-vig"),
    path("market/bulk-setvig/", BulkOverrideVigByIdsView.as_view(), name="bulk-market-set-vig"),
    path("bet-volume/", BetVolumeAdminView.as_view(), name="admin-bet-volume"),
    path("market/<int:market_id>/status/", MarketStatusUpdateAPIView.as_view(), name="market-status-update"),
    path("total-ggr/", TotalGGRAPIView.as_view(), name="total-ggr"),
    path("analytics/summary/", AdminAnalyticsAPIView.as_view(), name="analytics-summary"),
    path("analytics/dashboard/", AnalyticsDashboardAPIView.as_view(), name="analytics-dashboard"),

    path("analytics/dashboard-new/", AnalyticsDashboardAPIViewNew.as_view(), name="analytics-dashboard-new"),
    
    path("analytics/user-dashboard/", AnalyticsUserDashboardAPIView.as_view(), name="analytics-user-dashboard"),
    path("market/delete-exp/", DeleteExpiringMarketsView.as_view(), name="delete-expiring-markets"),
    path("platform_settings/", UpdatePlatformSettingsView.as_view(), name="update-platform-settings"),
    path("crs/", UpdateUserCRSView.as_view(), name="update-crs-value"),
    path("market/<int:market_id>/override/", AdminMarketOverrideAPIView.as_view(), name="market-override"),

    

    path("av-trade-volume/", AlphaVantageVolumeView.as_view(), name="alpha-trade-volume"),

    # KYC related URLs
    path("kyc/", AdminKYCViewSet.as_view({"get": "list"}),name="kyc_list"),
    path("kyc/<int:pk>/", AdminKYCViewSet.as_view({"get": "retrieve"}), name="kyc_detail"),
    path("kyc/<int:pk>/review/", AdminKYCViewSet.as_view({"patch": "review_kyc"}), name="kyc_review"),
    path("kyc/crs-risk/<int:user_id>/", CRSRiskScoreView.as_view(), name="crs-risk-score"),
    path("kyc/manual-trigger/<int:user_id>/", ManualKYCTriggerView.as_view(), name="manual-kyc-trigger"),
    path("kyc/crs-audit/<int:user_id>/", CRSRiskAuditLogView.as_view(), name="crs-audit-log"),
    path("bet-settlements/", AdminBetSettlementView.as_view(), name="admin-bet-settlements"),
    path("stocks/", StockListView.as_view(), name="stock-list"),
    path("stocks/settlements/", StockSettlementDetailView.as_view(), name="stock-settlement-detail"),
    path("stock/<int:pk>/toggle/", StockToggleUpdateView.as_view(), name="stock-toggle-update"),
    path("stock/refresh/", StockRefreshView.as_view(), name="stock-ticker-refresh"),
    path("markets/", GroupedMarketView.as_view(), name="grouped-market-view"),
    path("markets/<int:market_id>/nudge/", MarketOddsNudgeView.as_view(), name="nudge-market-view"),
    path("markets/<int:market_id>/reset/", MarketOddsResetView.as_view(), name="reset-market-view"),
    path("markets/suspended/", SuspendedMarketsView.as_view(), name="suspended-markets"),
    path("markets/suspended/<int:market_id>/", SuspendedMarketDetailView.as_view(), name="suspended-market-detail"),
]

#     # Odds related URLs
#     path("odds/update/<str:ticker>/", UpdateOddsView.as_view()),
#     path("odds/override/", odds.OddsOverrideView.as_view()),
#     path("odds/set-vig/", AdminSetVigView.as_view()),

#     # Dashboard related URLs
#     path("dashboard/kpis/", KPISummaryView.as_view()),
#     path("dashboard/summary/", MockAdminSummaryView.as_view()),

#     # User related URLs
#     path("users/search/", users.UserSearchView.as_view()),
#     path("users/<int:user_id>/history/", users.UserHistoryView.as_view()),
#     path("users/<int:user_id>/crs/", users.AdjustCRSView.as_view()),

#     # Risk related URLs
#     path("risk/", risk.RiskSettingsView.as_view()),

#     # Settlements related URLs
#     path("settlements/pending/", settlements.PendingSettlementsView.as_view()),
#     path("settlements/<int:bet_id>/resolve/", settlements.ResolveSettlementView.as_view()),

#     # Withdrawals related URLs
#     path("withdrawals/", withdrawals.WithdrawalListView.as_view()),
#     path("withdrawals/<int:withdrawal_id>/approve/", withdrawals.ApproveWithdrawalView.as_view()),

#     # Bets related URLs
#     path("admin/bets/open/", OpenBetsAdminView.as_view(), name="admin-open-bets"),
# ]
