import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/data/models/market_model_new.dart';
import 'package:frontend/app/modules/dashboard/domain/repositories/dashboard_repository_new.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';

/// Updated provider to return AppState<PaginatedMarketModel>
final getMarketsProviderNew =
    NotifierProvider<GetMarketsNotifierNew, AppState<PaginatedMarketModel>>(
  GetMarketsNotifierNew.new,
);

/// ✅ This lets you call: ref.read(updateSingleMarketProvider)(updatedMarket);
final updateSingleMarketProvider = Provider<void Function(MarketModel)>((ref) {
  return (MarketModel updatedMarket) {
    ref.read(getMarketsProviderNew.notifier).updateMarket(updatedMarket);
  };
});

class GetMarketsNotifierNew extends Notifier<AppState<PaginatedMarketModel>> {
  late final DashboardRepositoryNew _repo;

  @override
  AppState<PaginatedMarketModel> build() {
    _repo = ref.read(dashboardRepositoryNewProvider);
    return const Init();
  }

  /// Fetch markets (or others based on filters).
  /// When [preserveState] is true and we already have data, refresh in place
  /// so polling does not flash the UI back to a full loading state.
  void showLoading() {
    state = const LoadingState();
  }

  Future<void> get({
    Map<String, String>? queryParams,
    bool preserveState = false,
    bool preserveOrder = false,
  }) async {
    final previousState = state;
    final hasExistingData = previousState is SuccessState<PaginatedMarketModel> ||
        previousState is LoadMoreState<PaginatedMarketModel> ||
        previousState is ErrorDataState<PaginatedMarketModel>;

    if (!(preserveState && hasExistingData)) {
      state = const LoadingState();
    }

    final nextState = await _repo.getMarkets(queryParams: queryParams);

    if (preserveState &&
        hasExistingData &&
        nextState is ErrorState<PaginatedMarketModel>) {
      state = ErrorDataState(
        data: previousState.data,
        message: nextState.message,
      );
      return;
    }

    if (preserveState &&
        preserveOrder &&
        previousState is SuccessState<PaginatedMarketModel> &&
        nextState is SuccessState<PaginatedMarketModel>) {
      final previousResults = previousState.data.results;
      final fetchedResults = nextState.data.results;
      final fetchedById = {
        for (final market in fetchedResults) market.id: market,
      };

      final mergedResults = <MarketModel>[];
      final seenIds = <int>{};

      for (final market in previousResults) {
        final updatedMarket = fetchedById[market.id];
        if (updatedMarket == null) {
          continue;
        }
        mergedResults.add(updatedMarket);
        seenIds.add(market.id);
      }

      for (final market in fetchedResults) {
        if (!seenIds.contains(market.id)) {
          mergedResults.add(market);
        }
      }

      state = SuccessState(
        nextState.data.copyWith(results: mergedResults),
      );
      return;
    }

    state = nextState;
  }

  /// ✅ Update one market in the current list
   void updateMarket(MarketModel updated) {
      final current = state;
      if (current is SuccessState<PaginatedMarketModel>) {
        print("Updating market for symbol: ${updated.stock.symbol}");

        final index = current.data.results.indexWhere(
          (market) => market.stock.symbol == updated.stock.symbol,
        );

        if (index == -1) {
          print("⚠️ Market with symbol ${updated.stock.symbol} not found in current list.");
          return;
        }

        final updatedList = [...current.data.results];
        updatedList[index] = updated;

        print("✅ Replaced at index $index");

        final newData = current.data.copyWith(results: updatedList);
        state = SuccessState(newData);
      }
    }


}
