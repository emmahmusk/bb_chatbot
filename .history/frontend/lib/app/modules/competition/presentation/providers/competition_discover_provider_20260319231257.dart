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
  int _currentPage = 1;
  int _pageSize = 20;

  int get currentPage => _currentPage;
  int get pageSize => _pageSize;

  @override
  AppState<PaginatedCompetitionModel> build() {
    _repository = ref.read(competitionRepositoryProvider);
    return const Init();
  }

  Future<void> load({Map<String, String>? query, int? page, int? pageSize}) async {
    final pageToLoad = page ?? _currentPage;
    if (pageSize != null) _pageSize = pageSize;
    final baseQuery = query ?? _lastQuery;
    final resolvedQuery = {
      ...baseQuery,
      'page': '$pageToLoad',
      'page_size': '$_pageSize',
    };
    _lastQuery = Map<String, String>.from(baseQuery);
    _currentPage = pageToLoad;
    state = const LoadingState();
    state = await _repository.getCompetitions(queryParams: resolvedQuery);
  }

  Future<void> refresh() async {
    await load(query: _lastQuery, page: _currentPage);
  }

  Future<void> nextPage() async {
    if (!state.isSuccess) return;
    final next = _extractPage(state.data.next);
    if (next == null) return;
    await load(page: next);
  }

  Future<void> previousPage() async {
    if (!state.isSuccess) return;
    final previous = _extractPage(state.data.previous);
    if (previous == null) return;
    await load(page: previous);
  }

  int? _extractPage(String? url) {
    if (url == null || url.isEmpty) return null;
    return int.tryParse(Uri.parse(url).queryParameters['page'] ?? '');
  }
}
