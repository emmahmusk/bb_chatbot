import 'package:flutter_riverpod/flutter_riverpod.dart';
 

import '../../data/models/bet_history_model_new.dart';
import '../../domain/repositories/bet_history_repo_new.dart';

final betHistoryProvider =
    AsyncNotifierProvider<BetHistoryNotifier, List<BetHistoryModel>>(BetHistoryNotifier.new);

class BetHistoryNotifier extends AsyncNotifier<List<BetHistoryModel>> {
  final _repo = BetHistoryRepository();

  @override
  Future<List<BetHistoryModel>> build() async {
    return await _repo.fetchBetHistory();
  }

  /// To manually fetch and update state
  Future<void> get() async {
    state = const AsyncLoading();
    try {
      final data = await _repo.fetchBetHistory();
      state = AsyncData(data);
    } catch (e, st) {
      state = AsyncError(e, st);
    }
  }
}