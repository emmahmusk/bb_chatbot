import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/competition/data/models/competition_models.dart';
import 'package:frontend/app/modules/competition/domain/repositories/competition_repository.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';

final competitionDetailProvider =
    NotifierProvider<CompetitionDetailNotifier, AppState<CompetitionModel>>(
  CompetitionDetailNotifier.new,
);

class CompetitionDetailNotifier extends Notifier<AppState<CompetitionModel>> {
  late final CompetitionRepository _repository;
  int? _selectedCompetitionId;

  int? get selectedCompetitionId => _selectedCompetitionId;

  @override
  AppState<CompetitionModel> build() {
    _repository = ref.read(competitionRepositoryProvider);
    return const Init();
  }

  Future<void> load(int competitionId) async {
    _selectedCompetitionId = competitionId;
    state = const LoadingState();
    state = await _repository.getCompetitionDetail(competitionId);
  }

  Future<void> refresh() async {
    if (_selectedCompetitionId == null) return;
    await load(_selectedCompetitionId!);
  }
}
