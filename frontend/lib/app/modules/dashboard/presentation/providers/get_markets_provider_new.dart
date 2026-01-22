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

  /// Fetch trending markets (or others based on filters)
  Future<void> get({Map<String, String>? queryParams}) async {
    state = const LoadingState();
    state = await _repo.getMarkets(queryParams: queryParams);
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
