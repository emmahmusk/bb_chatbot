import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/competition/data/models/competition_models.dart';
import 'package:frontend/app/modules/competition/domain/repositories/competition_repository.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';

final competitionDiscoverProvider =
    NotifierProvider<CompetitionDiscoverNotifier, AppState<PaginatedCompetitionModel>>(
  CompetitionDiscoverNotifier.new,
);

class CompetitionDiscoverNotifier
    extends Notifier<AppState<PaginatedCompetitionModel>> {
  late final CompetitionRepository _repository;
  Map<String, String> _lastQuery = const {
    'status': 'registration',
    'registration_open': 'true',
    'ordering': 'start_date',
  };

  @override
  AppState<PaginatedCompetitionModel> build() {
    _repository = ref.read(competitionRepositoryProvider);
    return const Init();
  }

  Future<void> load({Map<String, String>? query}) async {
    final resolvedQuery = query ?? _lastQuery;
    _lastQuery = resolvedQuery;
    state = const LoadingState();
    state = await _repository.getCompetitions(queryParams: resolvedQuery);
  }

  Future<void> refresh() async {
    await load(query: _lastQuery);
  }
}
