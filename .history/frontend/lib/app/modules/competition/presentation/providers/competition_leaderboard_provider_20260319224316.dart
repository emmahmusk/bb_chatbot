import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/competition/data/models/competition_models.dart';
import 'package:frontend/app/modules/competition/domain/repositories/competition_repository.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';

final competitionLeaderboardProvider = NotifierProvider<
    CompetitionLeaderboardNotifier,
    AppState<PaginatedCompetitionLeaderboardModel>>(
  CompetitionLeaderboardNotifier.new,
);

class CompetitionLeaderboardNotifier
    extends Notifier<AppState<PaginatedCompetitionLeaderboardModel>> {
  late final CompetitionRepository _repository;
  int? _competitionId;

  @override
  AppState<PaginatedCompetitionLeaderboardModel> build() {
    _repository = ref.read(competitionRepositoryProvider);
    return const Init();
  }

  Future<void> load(int competitionId) async {
    _competitionId = competitionId;
    state = const LoadingState();
    state = await _repository.getLeaderboard(competitionId);
  }

  Future<void> refresh() async {
    if (_competitionId == null) return;
    await load(_competitionId!);
  }
}
