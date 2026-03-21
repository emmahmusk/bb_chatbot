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

class MobileCompetitionPage extends ConsumerStatefulWidget {
  const MobileCompetitionPage({super.key});

  @override
  ConsumerState<MobileCompetitionPage> createState() => _MobileCompetitionPageState();
}

enum _MobileCompetitionTab { discover, mine }

class _MobileCompetitionPageState extends ConsumerState<MobileCompetitionPage> {
  _MobileCompetitionTab _tab = _MobileCompetitionTab.discover;
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

  Future<void> _openCompetitionSheet(int competitionId) async {
    await ref.read(competitionDetailProvider.notifier).load(competitionId);
    await ref.read(competitionLeaderboardProvider.notifier).load(competitionId);

    if (!mounted) return;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _CompetitionDetailsSheet(),
    );
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
    await ref.read(competitionDiscoverProvider.notifier).refresh();
    if (isAuthenticated()) {
      await ref.read(competitionMyProvider.notifier).refresh();
    }
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
          await ref.read(competitionDiscoverProvider.notifier).refresh();
          await ref.read(competitionMyProvider.notifier).refresh();
          await _openCompetitionSheet(created.id);
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

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Competitions',
                    style: TextStyle(
                      color: colors.alwaysWhite,
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: _openCreateDialog,
                  icon: Icon(Icons.add_circle_outline, color: colors.alwaysWhite),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _tabChip(
                    label: 'Discover',
                    selected: _tab == _MobileCompetitionTab.discover,
                    onTap: () {
                      setState(() {
                        _tab = _MobileCompetitionTab.discover;
                      });
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _tabChip(
                    label: 'My Competitions',
                    selected: _tab == _MobileCompetitionTab.mine,
                    onTap: () async {
                      if (!isAuthenticated()) {
                        showCenterDialog(context, child: const LoginDialog());
                        return;
                      }
                      setState(() {
                        _tab = _MobileCompetitionTab.mine;
                      });
                      await myNotifier.load();
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: colors.always0D1117,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: colors.always30363D),
                ),
                child: _tab == _MobileCompetitionTab.discover
                    ? _CompetitionMobileList(
                        state: discoverState,
                        currentPage: discoverNotifier.currentPage,
                        onNext: discoverNotifier.nextPage,
                        onPrevious: discoverNotifier.previousPage,
                        onOpen: _openCompetitionSheet,
                        onJoin: _joinCompetition,
                        isJoining: _isJoining,
                      )
                    : _MyCompetitionMobileList(
                        state: myState,
                        currentPage: myNotifier.currentPage,
                        onNext: myNotifier.nextPage,
                        onPrevious: myNotifier.previousPage,
                        onOpen: _openCompetitionSheet,
                      ),
              ),
            ),
          ],
        ),
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
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: selected ? colors.always1F242C : colors.always0D1117,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: selected ? colors.always52AAFF : colors.always30363D,
          ),
        ),
        alignment: Alignment.center,
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
}

class _CompetitionMobileList extends ConsumerWidget {
  const _CompetitionMobileList({
    required this.state,
    required this.currentPage,
    required this.onNext,
    required this.onPrevious,
    required this.onOpen,
    required this.onJoin,
    required this.isJoining,
  });

  final AppState<PaginatedCompetitionModel> state;
  final int currentPage;
  final Future<void> Function() onNext;
  final Future<void> Function() onPrevious;
  final Future<void> Function(int competitionId) onOpen;
  final Future<void> Function(CompetitionModel competition) onJoin;
  final bool isJoining;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (state.isError) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            state.errorMessage,
            style: TextStyle(color: colors.alwaysFF4C4C),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    if (!state.isSuccess || state.data.results.isEmpty) {
      return const EmptyState(
        title: 'No competitions available',
        message: 'Create one and invite users to join.',
      );
    }

    final data = state.data;

    return Column(
      children: [
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.all(12),
            itemBuilder: (_, index) {
              final item = data.results[index];
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: colors.always161B22,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: colors.always30363D),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.name,
                      style: TextStyle(
                        color: colors.alwaysWhite,
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      item.description ?? 'No description',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: colors.always8B949E, fontSize: 12),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      '${item.memberCount}/${item.maxMembers} members • ${item.entryFee} BBC',
                      style: TextStyle(color: colors.alwaysE6EDF3, fontSize: 12),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: CustomOutlinedButton.big(
                            text: 'View',
                            onTap: () => onOpen(item.id),
                            textColor: colors.alwaysE6EDF3,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: CustomButton(
                            text: _joinLabel(item, isJoining),
                            fontSize: 13,
                            onPressed: _canJoin(item) && !isJoining
                                ? () => onJoin(item)
                                : null,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemCount: data.results.length,
          ),
        ),
        CompetitionPaginationBar(
          currentPage: currentPage,
          hasPrevious: data.previous != null,
          hasNext: data.next != null,
          onPrevious: onPrevious,
          onNext: onNext,
        ),
      ],
    );
  }

  String _joinLabel(CompetitionModel item, bool isJoining) {
    if (item.userJoined) return 'Joined';
    if (item.isFull) return 'Full';
    if (!item.isRegistrationOpen) return 'Closed';
    return isJoining ? 'Joining...' : 'Join';
  }

  bool _canJoin(CompetitionModel item) {
    return !item.userJoined && item.isRegistrationOpen && !item.isFull;
  }
}

class _MyCompetitionMobileList extends ConsumerWidget {
  const _MyCompetitionMobileList({
    required this.state,
    required this.currentPage,
    required this.onNext,
    required this.onPrevious,
    required this.onOpen,
  });

  final AppState<PaginatedCompetitionMembershipModel> state;
  final int currentPage;
  final Future<void> Function() onNext;
  final Future<void> Function() onPrevious;
  final Future<void> Function(int competitionId) onOpen;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (state.isError) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            state.errorMessage,
            style: TextStyle(color: colors.alwaysFF4C4C),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    if (!state.isSuccess || state.data.results.isEmpty) {
      return const EmptyState(
        title: 'No joined competitions',
        message: 'Join one from the Discover tab.',
      );
    }

    final data = state.data;

    return Column(
      children: [
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.all(12),
            itemBuilder: (_, index) {
              final item = data.results[index];
              return Container(
                padding: const EdgeInsets.all(12),
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
                              fontWeight: FontWeight.w700,
                              fontSize: 15,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Joined as @${item.username}',
                            style: TextStyle(color: colors.always8B949E, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    CustomOutlinedButton.big(
                      text: 'Open',
                      onTap: () => onOpen(item.competition),
                      textColor: colors.alwaysE6EDF3,
                    ),
                  ],
                ),
              );
            },
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemCount: data.results.length,
          ),
        ),
        CompetitionPaginationBar(
          currentPage: currentPage,
          hasPrevious: data.previous != null,
          hasNext: data.next != null,
          onPrevious: onPrevious,
          onNext: onNext,
        ),
      ],
    );
  }
}

class _CompetitionDetailsSheet extends ConsumerWidget {
  const _CompetitionDetailsSheet();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    final detailState = ref.watch(competitionDetailProvider);
    final leaderboardState = ref.watch(competitionLeaderboardProvider);
    final leaderboardNotifier = ref.read(competitionLeaderboardProvider.notifier);

    return Container(
      decoration: BoxDecoration(
        color: colors.always0D1117,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(18)),
        border: Border.all(color: colors.always30363D),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.82,
          child: Column(
            children: [
              const SizedBox(height: 10),
              Container(
                width: 44,
                height: 4,
                decoration: BoxDecoration(
                  color: colors.always30363D,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
              Expanded(
                child: detailState.isSuccess
                    ? Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              detailState.data.name,
                              style: TextStyle(
                                color: colors.alwaysWhite,
                                fontSize: 20,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              detailState.data.description ?? 'No description',
                              style: TextStyle(color: colors.always8B949E),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'Leaderboard',
                              style: TextStyle(
                                color: colors.alwaysWhite,
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Expanded(
                              child: leaderboardState.isSuccess
                                  ? ListView.separated(
                                      itemBuilder: (_, index) {
                                        final row = leaderboardState.data.results[index];
                                        return ListTile(
                                          contentPadding: EdgeInsets.zero,
                                          title: Text(
                                            row.username,
                                            style: TextStyle(color: colors.alwaysWhite),
                                          ),
                                          subtitle: Text(
                                            'ROI ${row.roi.toStringAsFixed(2)}% • P/L ${row.netProfit.toStringAsFixed(2)}',
                                            style: TextStyle(color: colors.always8B949E),
                                          ),
                                        );
                                      },
                                      separatorBuilder: (_, __) => Divider(color: colors.always30363D),
                                      itemCount: leaderboardState.data.results.length,
                                    )
                                  : leaderboardState.isLoading
                                      ? const Center(child: CircularProgressIndicator())
                                      : Center(
                                          child: Text(
                                            leaderboardState.errorMessage,
                                            style: TextStyle(color: colors.alwaysFF4C4C),
                                          ),
                                        ),
                            ),
                            if (leaderboardState.isSuccess)
                              CompetitionPaginationBar(
                                currentPage: leaderboardNotifier.currentPage,
                                hasPrevious: leaderboardState.data.previous != null,
                                hasNext: leaderboardState.data.next != null,
                                onPrevious: leaderboardNotifier.previousPage,
                                onNext: leaderboardNotifier.nextPage,
                              ),
                          ],
                        ),
                      )
                    : detailState.isLoading
                        ? const Center(child: CircularProgressIndicator())
                        : Center(
                            child: Padding(
                              padding: const EdgeInsets.all(20),
                              child: Text(
                                detailState.errorMessage,
                                style: TextStyle(color: colors.alwaysFF4C4C),
                              ),
                            ),
                          ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
