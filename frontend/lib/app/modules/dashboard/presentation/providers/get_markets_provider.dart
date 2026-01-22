import 'package:frontend/app/modules/dashboard/data/models/markets_model.dart';
import 'package:frontend/app/modules/dashboard/domain/repositories/dashboard_repository.dart';
import 'package:frontend/app/shared/extensions/api_future_extension.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';

final getMarketsProvider =
    AppNotifierProvider<GetMarketsNotifier, List<MarketModel>>(
  GetMarketsNotifier.new,
);

class GetMarketsNotifier extends AppNotifier<List<MarketModel>> {
  late final DashboardRepository repo;
  @override
  AppState<List<MarketModel>> build() {
    repo = ref.read(dashboardRepositoryProvider);
    return const Init();
  }

  void get() async {
    state = const LoadingState();
    state = await repo.getMarkets().toState;
  }
}
