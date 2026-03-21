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
  int _currentPage = 1;
  int _pageSize = 20;

  int get currentPage => _currentPage;
  int get pageSize => _pageSize;

  @override
  AppState<PaginatedCompetitionLeaderboardModel> build() {
    _repository = ref.read(competitionRepositoryProvider);
    return const Init();
  }

  Future<void> load(int competitionId, {int? page, int? pageSize}) async {
    _competitionId = competitionId;
    _currentPage = page ?? _currentPage;
    if (pageSize != null) _pageSize = pageSize;
    state = const LoadingState();
    state = await _repository.getLeaderboard(
      competitionId,
      queryParams: {'page': '$_currentPage', 'page_size': '$_pageSize'},
    );
  }

  Future<void> refresh() async {
    if (_competitionId == null) return;
    await load(_competitionId!, page: _currentPage);
  }

  Future<void> nextPage() async {
    if (_competitionId == null || !state.isSuccess) return;
    final next = _extractPage(state.data.next);
    if (next == null) return;
    await load(_competitionId!, page: next);
  }

  Future<void> previousPage() async {
    if (_competitionId == null || !state.isSuccess) return;
    final previous = _extractPage(state.data.previous);
    if (previous == null) return;
    await load(_competitionId!, page: previous);
  }

  int? _extractPage(String? url) {
    if (url == null || url.isEmpty) return null;
    return int.tryParse(Uri.parse(url).queryParameters['page'] ?? '');
  }
}
