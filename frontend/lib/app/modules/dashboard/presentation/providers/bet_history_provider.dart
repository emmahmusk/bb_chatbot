import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/bet_history_model.dart';
import '../../domain/repositories/bet_history_repo.dart';

final betHistoryRepositoryProvider = Provider((ref) => BetHistoryRepository());

final betHistoryProvider = FutureProvider<List<BetHistoryModel>>((ref) async {
  final repo = ref.read(betHistoryRepositoryProvider);
  return await repo.getBetHistory();
});
