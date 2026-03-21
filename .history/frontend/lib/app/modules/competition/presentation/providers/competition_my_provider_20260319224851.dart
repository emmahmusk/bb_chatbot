import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/competition/data/models/competition_models.dart';
import 'package:frontend/app/modules/competition/domain/repositories/competition_repository.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';

final competitionMyProvider =
    NotifierProvider<CompetitionMyNotifier, AppState<PaginatedCompetitionMembershipModel>>(
  CompetitionMyNotifier.new,
);

class CompetitionMyNotifier
    extends Notifier<AppState<PaginatedCompetitionMembershipModel>> {
  late final CompetitionRepository _repository;

  @override
  AppState<PaginatedCompetitionMembershipModel> build() {
    _repository = ref.read(competitionRepositoryProvider);
    return const Init();
  }

  Future<void> load() async {
    state = const LoadingState();
    state = await _repository.getMyCompetitions();
  }

  Future<void> refresh() async {
    await load();
  }
}
