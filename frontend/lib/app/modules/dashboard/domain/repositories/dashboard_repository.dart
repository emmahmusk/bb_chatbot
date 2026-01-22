import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/data/dtos/parlay_bet_dto.dart';
import 'package:frontend/app/modules/dashboard/data/dtos/single_bet_dto.dart';
import 'package:frontend/app/modules/dashboard/data/models/markets_model.dart';
import 'package:frontend/app/modules/dashboard/data/models/parlay_bet_model.dart';
import 'package:frontend/app/modules/dashboard/data/models/single_bet_model.dart';
import 'package:frontend/app/modules/dashboard/domain/endpoints/dashboard_endpoints.dart';
import 'package:frontend/app/shared/classes/http/http.dart';
import 'package:frontend/app/shared/functions/api_functions.dart';

final dashboardRepositoryProvider = Provider((ref) {
  final http = ref.read(httpProvider);
  return DashboardRepository(http: http);
});

class DashboardRepository {
  final HTTP http;

  DashboardRepository({required this.http});

  ApiFuture<List<MarketModel>> getMarkets() {
    return getCall(
      http,
      endpoint: DashboardEndpoints.markets,
      onResponseBody: (r, _) {
        final now = DateTime.now();
        final upcoming = List.from(r)
            .map((e) => MarketModel.fromJson(e))
            .where((e) => e.expiryDate.isAfter(now))
            .toList();

        upcoming.sort((a, b) => a.expiryDate.compareTo(b.expiryDate));

        return upcoming;
      },
    );
  }

  ApiFuture<SingleBetModel> placeSingleBet(SingleBetDto dto) {
    return postCall(
      http,
      endpoint: DashboardEndpoints.singleBet,
      acceptableStatusCodes: [200, 201],
      onResponseBody: (r, _) {
        return SingleBetModel.fromJson(r['bet']);
      },
      body: dto.toJson(),
    );
  }

  ApiFuture<ParlayBetModel> placeParlayBet(ParlayBetDto dto) {
    return postCall(
      http,
      endpoint: DashboardEndpoints.parlayBet,
      acceptableStatusCodes: [200, 201],
      onResponseBody: (r, _) {
        return ParlayBetModel.fromJson(r['parlay_bet']);
      },
      body: dto.toJson(),
    );
  }
}
