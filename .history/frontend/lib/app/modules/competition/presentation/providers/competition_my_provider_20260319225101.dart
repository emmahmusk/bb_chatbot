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
  int _currentPage = 1;

  int get currentPage => _currentPage;

  @override
  AppState<PaginatedCompetitionMembershipModel> build() {
    _repository = ref.read(competitionRepositoryProvider);
    return const Init();
  }

  Future<void> load({int? page}) async {
    _currentPage = page ?? _currentPage;
    state = const LoadingState();
    state = await _repository.getMyCompetitions(
      queryParams: {'page': '$_currentPage'},
    );
  }

  Future<void> refresh() async {
    await load(page: _currentPage);
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
