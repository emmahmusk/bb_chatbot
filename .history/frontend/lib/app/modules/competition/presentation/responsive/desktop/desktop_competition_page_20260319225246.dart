import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/modules/competition/data/models/competition_models.dart';
import 'package:frontend/app/modules/competition/domain/repositories/competition_repository.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_detail_provider.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_discover_provider.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_leaderboard_provider.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_my_provider.dart';
import 'package:frontend/app/modules/competition/presentation/widgets/competition_create_dialog.dart';
import 'package:frontend/app/modules/competition/presentation/widgets/competition_pagination_bar.dart';
import 'package:frontend/app/shared/extensions/context_extension.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/empty_state.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class DesktopCompetitionPage extends ConsumerStatefulWidget {
  const DesktopCompetitionPage({super.key});

  @override
  ConsumerState<DesktopCompetitionPage> createState() =>
      _DesktopCompetitionPageState();
}

enum _CompetitionTab { discover, myCompetitions }

class _DesktopCompetitionPageState extends ConsumerState<DesktopCompetitionPage> {
  _CompetitionTab _activeTab = _CompetitionTab.discover;
  bool _isJoining = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      await ref.read(competitionDiscoverProvider.notifier).load();
      if (isAuthenticated()) {
        await ref.read(competitionMyProvider.notifier).load();
      }
    });
  }

  Future<void> _openCompetition(int competitionId) async {
    await ref.read(competitionDetailProvider.notifier).load(competitionId);
    await ref.read(competitionLeaderboardProvider.notifier).load(competitionId);
  }

  Future<void> _refreshData() async {
    await ref.read(competitionDiscoverProvider.notifier).refresh();
    if (isAuthenticated()) {
      await ref.read(competitionMyProvider.notifier).refresh();
    }
    await ref.read(competitionDetailProvider.notifier).refresh();
    await ref.read(competitionLeaderboardProvider.notifier).refresh();
  }

  Future<void> _joinCompetition(CompetitionModel competition) async {
    if (!isAuthenticated()) {
      showCenterDialog(context, child: const LoginDialog());
      return;
    }

    setState(() {
      _isJoining = true;
    });

    final result = await ref
        .read(competitionRepositoryProvider)
        .joinCompetition(competition.id);

    if (!mounted) return;

    setState(() {
      _isJoining = false;
    });

    if (result.isError) {
      context.showError(result.errorMessage);
      return;
    }

    context.showSuccess(result.data.message);
    await _refreshData();
  }

  void _openCreateDialog() {
    if (!isAuthenticated()) {
      showCenterDialog(context, child: const LoginDialog());
      return;
    }

    showDialog<void>(
      context: context,
      builder: (_) => CompetitionCreateDialog(
        onCreated: (created) async {
          await _refreshData();
          await _openCompetition(created.id);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final discoverState = ref.watch(competitionDiscoverProvider);
    final discoverNotifier = ref.read(competitionDiscoverProvider.notifier);
    final myState = ref.watch(competitionMyProvider);
    final myNotifier = ref.read(competitionMyProvider.notifier);
    final detailState = ref.watch(competitionDetailProvider);
    final leaderboardState = ref.watch(competitionLeaderboardProvider);
    final leaderboardNotifier = ref.read(competitionLeaderboardProvider.notifier);

    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Competitions',
                style: TextStyle(
                  color: colors.alwaysWhite,
                  fontSize: 30,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 14),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: colors.always1F242C,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: colors.always30363D),
                ),
                child: Text(
                  'Community Leagues',
                  style: TextStyle(
                    color: colors.always8B949E,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const Spacer(),
              CustomOutlinedButton.big(
                text: 'Refresh',
                onTap: _refreshData,
                textColor: colors.alwaysE6EDF3,
              ),
              const SizedBox(width: 10),
              CustomButton(
                text: 'Create Competition',
                fontSize: 14,
                width: 180,
                onPressed: _openCreateDialog,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              _tabChip(
                label: 'Discover',
                selected: _activeTab == _CompetitionTab.discover,
                onTap: () {
                  setState(() {
                    _activeTab = _CompetitionTab.discover;
                  });
                },
              ),
              const SizedBox(width: 10),
              _tabChip(
                label: 'My Competitions',
                selected: _activeTab == _CompetitionTab.myCompetitions,
                onTap: () async {
                  if (!isAuthenticated()) {
                    showCenterDialog(context, child: const LoginDialog());
                    return;
                  }
                  setState(() {
                    _activeTab = _CompetitionTab.myCompetitions;
                  });
                  await ref.read(competitionMyProvider.notifier).load();
                },
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 5,
                  child: Container(
                    decoration: BoxDecoration(
                      color: colors.always0D1117,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: colors.always30363D),
                    ),
                    child: _buildListPanel(
                      discoverState: discoverState,
                      discoverCurrentPage: discoverNotifier.currentPage,
                      onDiscoverNext: discoverNotifier.nextPage,
                      onDiscoverPrevious: discoverNotifier.previousPage,
                      myState: myState,
                      myCurrentPage: myNotifier.currentPage,
                      onMyNext: myNotifier.nextPage,
                      onMyPrevious: myNotifier.previousPage,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  flex: 4,
                  child: Container(
                    decoration: BoxDecoration(
                      color: colors.always0D1117,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: colors.always30363D),
                    ),
                    child: _buildDetailPanel(
                      detailState: detailState,
                      leaderboardState: leaderboardState,
                      leaderboardCurrentPage: leaderboardNotifier.currentPage,
                      onLeaderboardNext: leaderboardNotifier.nextPage,
                      onLeaderboardPrevious: leaderboardNotifier.previousPage,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildListPanel({
    required AppState<PaginatedCompetitionModel> discoverState,
    required int discoverCurrentPage,
    required Future<void> Function() onDiscoverNext,
    required Future<void> Function() onDiscoverPrevious,
    required AppState<PaginatedCompetitionMembershipModel> myState,
    required int myCurrentPage,
    required Future<void> Function() onMyNext,
    required Future<void> Function() onMyPrevious,
  }) {
    final colors = ref.watch(appThemeProvider).colors;

    if (_activeTab == _CompetitionTab.discover) {
      if (discoverState.isLoading) {
        return const Center(child: CircularProgressIndicator());
      }
      if (discoverState.isError) {
        return _panelMessage(discoverState.errorMessage, isError: true);
      }
      if (!discoverState.isSuccess || discoverState.data.results.isEmpty) {
        return const EmptyState(
          title: 'No competitions available',
          message: 'Create one and invite people to join.',
        );
      }

      final items = discoverState.data.results;
      return Column(
        children: [
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.all(14),
              itemBuilder: (_, index) {
                final item = items[index];
                return _competitionCard(item: item);
              },
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemCount: items.length,
            ),
          ),
          CompetitionPaginationBar(
            currentPage: discoverCurrentPage,
            hasPrevious: discoverState.data.previous != null,
            hasNext: discoverState.data.next != null,
            onPrevious: onDiscoverPrevious,
            onNext: onDiscoverNext,
          ),
        ],
      );
    }

    if (myState.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (myState.isError) {
      return _panelMessage(myState.errorMessage, isError: true);
    }
    if (!myState.isSuccess || myState.data.results.isEmpty) {
      return const EmptyState(
        title: 'No joined competitions',
        message: 'Open Discover and join one to appear here.',
      );
    }

    final items = myState.data.results;
    return Column(
      children: [
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.all(14),
            itemBuilder: (_, index) {
              final item = items[index];
              return Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: colors.always161B22,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: colors.always30363D),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.competitionName,
                            style: TextStyle(
                              color: colors.alwaysWhite,
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Joined as @${item.username}',
                            style: TextStyle(
                              color: colors.always8B949E,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                    CustomOutlinedButton.big(
                      text: 'Open',
                      onTap: () => _openCompetition(item.competition),
                      textColor: colors.alwaysE6EDF3,
                    ),
                  ],
                ),
              );
            },
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemCount: items.length,
          ),
        ),
        CompetitionPaginationBar(
          currentPage: myCurrentPage,
          hasPrevious: myState.data.previous != null,
          hasNext: myState.data.next != null,
          onPrevious: onMyPrevious,
          onNext: onMyNext,
        ),
      ],
    );
  }

  Widget _competitionCard({required CompetitionModel item}) {
    final colors = ref.watch(appThemeProvider).colors;
    final memberPercent =
        item.maxMembers == 0 ? 0.0 : (item.memberCount / item.maxMembers).clamp(0, 1);
    final statusColor = switch (item.status) {
      'active' => colors.always27D07F,
      'completed' => colors.always8B949E,
      'cancelled' => colors.alwaysFF4C4C,
      _ => colors.always52AAFF,
    };

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colors.always161B22,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.always30363D),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  item.name,
                  style: TextStyle(
                    color: colors.alwaysWhite,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: statusColor),
                ),
                child: Text(
                  item.status.toUpperCase(),
                  style: TextStyle(
                    color: statusColor,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            item.description ?? 'No description',
            style: TextStyle(
              color: colors.always8B949E,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Members ${item.memberCount}/${item.maxMembers}',
            style: TextStyle(color: colors.alwaysE6EDF3, fontSize: 12),
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: memberPercent,
              minHeight: 8,
              backgroundColor: colors.always2D333B,
              valueColor: AlwaysStoppedAnimation<Color>(colors.always52AAFF),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: Text(
                  'Entry fee: ${item.entryFee} BBC',
                  style: TextStyle(color: colors.alwaysE6EDF3, fontSize: 12),
                ),
              ),
              CustomOutlinedButton.big(
                text: 'Details',
                onTap: () => _openCompetition(item.id),
                textColor: colors.alwaysE6EDF3,
              ),
              const SizedBox(width: 8),
              CustomButton(
                text: _joinLabel(item),
                onPressed: _canJoin(item) && !_isJoining
                    ? () => _joinCompetition(item)
                    : null,
                width: 120,
                fontSize: 13,
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _joinLabel(CompetitionModel item) {
    if (item.userJoined) return 'Joined';
    if (item.isFull) return 'Full';
    if (!item.isRegistrationOpen) return 'Closed';
    return _isJoining ? 'Joining...' : 'Join';
  }

  bool _canJoin(CompetitionModel item) {
    return !item.userJoined && item.isRegistrationOpen && !item.isFull;
  }

  Widget _buildDetailPanel({
    required AppState<CompetitionModel> detailState,
    required AppState<PaginatedCompetitionLeaderboardModel> leaderboardState,
    required int leaderboardCurrentPage,
    required Future<void> Function() onLeaderboardNext,
    required Future<void> Function() onLeaderboardPrevious,
  }) {
    final colors = ref.watch(appThemeProvider).colors;

    if (detailState.isInitial) {
      return _panelMessage('Select a competition to view full details and leaderboard.');
    }

    if (detailState.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (detailState.isError) {
      return _panelMessage(detailState.errorMessage, isError: true);
    }

    final item = detailState.data;

    return Padding(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item.name,
            style: TextStyle(
              color: colors.alwaysWhite,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            item.description ?? 'No description provided.',
            style: TextStyle(color: colors.always8B949E),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _pill('Status: ${item.status}'),
              _pill('Scoring: ${item.scoringMethod}'),
              _pill('Members: ${item.memberCount}/${item.maxMembers}'),
              _pill('Fee: ${item.entryFee} BBC'),
            ],
          ),
          const SizedBox(height: 12),
          if (item.startDate != null)
            Text(
              'Starts: ${_formatDate(item.startDate!)}',
              style: TextStyle(color: colors.alwaysE6EDF3, fontSize: 12),
            ),
          const SizedBox(height: 2),
          if (item.endDate != null)
            Text(
              'Ends: ${_formatDate(item.endDate!)}',
              style: TextStyle(color: colors.alwaysE6EDF3, fontSize: 12),
            ),
          const SizedBox(height: 16),
          Text(
            'Leaderboard',
            style: TextStyle(
              color: colors.alwaysWhite,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: _buildLeaderboard(
              leaderboardState: leaderboardState,
              leaderboardCurrentPage: leaderboardCurrentPage,
              onLeaderboardNext: onLeaderboardNext,
              onLeaderboardPrevious: onLeaderboardPrevious,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLeaderboard({
    required AppState<PaginatedCompetitionLeaderboardModel> leaderboardState,
    required int leaderboardCurrentPage,
    required Future<void> Function() onLeaderboardNext,
    required Future<void> Function() onLeaderboardPrevious,
  }) {
    final colors = ref.watch(appThemeProvider).colors;

    if (leaderboardState.isInitial || leaderboardState.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (leaderboardState.isError) {
      return _panelMessage(leaderboardState.errorMessage, isError: true);
    }

    final rows = leaderboardState.data.results;
    if (rows.isEmpty) {
      return const EmptyState(
        title: 'No participants yet',
        message: 'Once users join, leaderboard rankings will appear here.',
      );
    }

    return Column(
      children: [
        Expanded(
          child: ListView.separated(
            itemBuilder: (_, index) {
              final row = rows[index];
              final rank = row.finalRank ?? (index + 1);
              return Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: colors.always161B22,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: colors.always30363D),
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 15,
                      backgroundColor: colors.always2D333B,
                      child: Text(
                        '$rank',
                        style: TextStyle(
                          color: colors.alwaysWhite,
                          fontWeight: FontWeight.w700,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        row.username,
                        style: TextStyle(
                          color: colors.alwaysWhite,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    Text(
                      'ROI ${row.roi.toStringAsFixed(2)}%',
                      style: TextStyle(color: colors.always52AAFF, fontSize: 12),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      'P/L ${row.netProfit.toStringAsFixed(2)}',
                      style: TextStyle(
                        color: row.netProfit >= 0
                            ? colors.always27D07F
                            : colors.alwaysFF4C4C,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              );
            },
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemCount: rows.length,
          ),
        ),
        CompetitionPaginationBar(
          currentPage: leaderboardCurrentPage,
          hasPrevious: leaderboardState.data.previous != null,
          hasNext: leaderboardState.data.next != null,
          onPrevious: onLeaderboardPrevious,
          onNext: onLeaderboardNext,
        ),
      ],
    );
  }

  Widget _pill(String text) {
    final colors = ref.watch(appThemeProvider).colors;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: colors.always1F242C,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: colors.always30363D),
      ),
      child: Text(
        text,
        style: TextStyle(color: colors.alwaysE6EDF3, fontSize: 12),
      ),
    );
  }

  Widget _tabChip({
    required String label,
    required bool selected,
    required VoidCallback onTap,
  }) {
    final colors = ref.watch(appThemeProvider).colors;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? colors.always1F242C : colors.always0D1117,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: selected ? colors.always52AAFF : colors.always30363D,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? colors.alwaysWhite : colors.always8B949E,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }

  Widget _panelMessage(String message, {bool isError = false}) {
    final colors = ref.watch(appThemeProvider).colors;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Text(
          message,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: isError ? colors.alwaysFF4C4C : colors.always8B949E,
            fontSize: 14,
          ),
        ),
      ),
    );
  }

  String _formatDate(DateTime date) {
    final d = date.toLocal();
    final month = d.month.toString().padLeft(2, '0');
    final day = d.day.toString().padLeft(2, '0');
    final hour = d.hour.toString().padLeft(2, '0');
    final minute = d.minute.toString().padLeft(2, '0');
    return '${d.year}-$month-$day $hour:$minute';
  }
}
