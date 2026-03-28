from django.urls import path

from . import api, views
from .api_competition_member import CompetitionMemberListAPIView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("login/", api.LoginAPIView.as_view(), name="login"),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("signup/", api.SignupAPIView.as_view(), name="register"),
    path("profile/", api.RetrieveUpdateProfileAPIView.as_view(), name="profile-retrieve"),
    path("profile/update/", api.RetrieveUpdateProfileAPIView.as_view(), name="profile-update"),
    path("profile/create/", api.RetrieveUpdateProfileAPIView.as_view(), name="profile-create"),
    path("bet-info/", views.UserBetsAPIView.as_view(), name="user_balance_info"),
    # path("verify_email/", api.VerifyEmailAPIView.as_view(), name="verify-email"),
    path("bet_history/", views.UserBetHistoryAPIView.as_view(), name="bet-history"),
    path("bet_preference/", views.BettingPreferenceView.as_view(), name="bet-preference"),
    path("mykyc/upload/", api.KYCFileUploadAPIView.as_view(), name="mykyc-upload"),
    path("mykyc/", views.UserKPIsOverviewAPIView.as_view(), name="mykyc-overview"),
    path("pass_reset/request/", views.PasswordResetOTPRequestView.as_view(), name="pass-reset-request"),
    path("pass_reset/verify/", views.PasswordResetOTPVerifyView.as_view(), name="pass-reset-verify"),
    path("verify_email/request/", views.VerifyEmailRequestOTP.as_view(), name="verify-email-request"),
    path("email/verify/", views.VerifyEmailOTPVerify.as_view(), name="email-verify"),
    path("wallet/fund/", api.WalletFundView.as_view(), name="fund-wallet"),
    path("wallet/history/", api.WalletTransactionHistoryView.as_view(), name="wallet-history"),
    path("wallet/withdraw/", api.WalletWithdrawView.as_view(), name="wallet-withdraw"),
    path("wallet/coins/summary/", api.WalletCoinSummaryView.as_view(), name="wallet-coins-summary"),
    path("wallet/coins/conversion-table/", api.WalletCoinConversionTableView.as_view(), name="wallet-coins-conversion-table"),
    path("wallet/coins/reward/", api.WalletCoinRewardView.as_view(), name="wallet-coins-reward"),
    path("wallet/coins/convert-to-cash/", api.WalletCoinConvertToCashView.as_view(), name="wallet-coins-convert-to-cash"),
    path("wallet/coins/redeem/", api.WalletCoinRedeemView.as_view(), name="wallet-coins-redeem"),
    path("wallet/coins/conversion-preview/", api.WalletCoinConversionPreviewView.as_view(), name="wallet-coins-conversion-preview"),

    # Competition membership wallet API
    path("competition/memberships/", CompetitionMemberListAPIView.as_view(), name="competition-memberships"),
]
