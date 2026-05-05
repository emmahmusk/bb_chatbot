from django.urls import path

from .views import (
    CleanOldOptionsView, AggregatedDataGapView, DataGapView, 
    BulkPopulateMarketFromOptionsView, OptionDataListView, PopulateMarketFromOptionsView, 
    PopulateStockAPIView, StockListAPIView, TriggerOptionIngestView, TriggerSteadyAPIOptionIngestView
)

urlpatterns = [
    path("populate-stocks/", PopulateStockAPIView.as_view(), name="populate-stocks"),
    path("stocks/", StockListAPIView.as_view(), name="stock-list"),
    path('ingest-options/', TriggerOptionIngestView.as_view(), name='ingest-options'),
    path('ingest-options-steady/', TriggerSteadyAPIOptionIngestView.as_view(), name='ingest-options-steady'),
    path("option-data/", OptionDataListView.as_view(), name="option-data-list"),
    path('datagap/', AggregatedDataGapView.as_view(), name='agg-datagap'),
    path('clean-options/', CleanOldOptionsView.as_view(), name='clean-options'),
    path('datagap-single/', DataGapView.as_view(), name='datagap-single'),
    path('pop-market/', PopulateMarketFromOptionsView.as_view(), name='pop_market'),
    path('bulk-pop-mkt/', BulkPopulateMarketFromOptionsView.as_view(), name='bulk_market_data_api'),
]
