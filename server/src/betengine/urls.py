from django.urls import path

from .views import CompetitionDetailAPIView, CompetitionJoinAPIView, CompetitionLeaderboardAPIView, CompetitionListCreateAPIView, CompetitionMembershipListAPIView, ExpiryDatesByStockSymbolView, LoadStockTagsView, MarketByExpiryDateView, MarketDetailAPIView, MarketListAPIView, PopulateMarketsView, StockSearchWithTagsAPIView, StrikePricesByStockSymbolView  # New
from .views import PlaceParlayBetAPIView  # New
from .views import PlaceSingleBetAPIView  # New
from .views import (
    BetListAPIView,
    BetResolutionAPIView,
    ParlayBetListAPIView,
    ParlayBetResolutionAPIView,
    ResolveExpiredMarketsAPIView,
    CreditWinningBetsAPIView
)

urlpatterns = [
    path("stocks/load-tags/", LoadStockTagsView.as_view(), name="load-stock-tags"),
    path("stocks/search-with-tags/", StockSearchWithTagsAPIView.as_view(), name="stock-search-with-tags"),
    path("populate_market/", PopulateMarketsView.as_view(), name="populate-market"),  # New
    path("markets/", MarketListAPIView.as_view(), name="market-list"),  # New
    path("markets_by_expiry/", MarketByExpiryDateView.as_view(), name="market-by-expiry"),
    path("expiries/", ExpiryDatesByStockSymbolView.as_view(), name="expiries-by-stock"),  # New
    path("strike_prices/", StrikePricesByStockSymbolView.as_view(), name="expiries-by-stock"),
    path("markets/<int:pk>/", MarketDetailAPIView.as_view(), name="market-detailed-list"),
    path("single/", PlaceSingleBetAPIView.as_view(), name="place-single-bet"),  # New
    path("parlay/", PlaceParlayBetAPIView.as_view(), name="place-parlay-bet"),  # New
    path("list/", BetListAPIView.as_view(), name="bet-list"),  # New
    path("bulk_resolve/", ResolveExpiredMarketsAPIView.as_view(), name="bulk-resolve"),
    path(
        "single/resolve/", BetResolutionAPIView.as_view(), name="single-resolve"
    ),  # New
    path(
        "parlay/resolve/", ParlayBetResolutionAPIView.as_view(), name="parlay-resolve"                             
    ),  # New
    path("parlay/list/", ParlayBetListAPIView.as_view(), name="parlay-list"),  # New
    path("wallets/bulk-cr/", CreditWinningBetsAPIView.as_view(), name="credit-wallets"),
    path("competitions/", CompetitionListCreateAPIView.as_view(), name="competition-list-create"),
    path("competitions/<int:pk>/", CompetitionDetailAPIView.as_view(), name="competition-detail"),
    path("competitions/<int:competition_id>/join/", CompetitionJoinAPIView.as_view(), name="competition-join"),
    path("competitions/<int:competition_id>/leaderboard/", CompetitionLeaderboardAPIView.as_view(), name="competition-leaderboard"),
    path("competitions/my/", CompetitionMembershipListAPIView.as_view(), name="competition-membership-list"),
]
