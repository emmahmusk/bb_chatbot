import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/modules/competition/data/models/competition_models.dart';
import 'package:frontend/app/modules/competition/domain/repositories/competition_repository.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_detail_provider.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_discover_provider.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_leaderboard_provider.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_my_provider.dart';
import 'package:frontend/app/modules/competition/presentation/widgets/competition_create_dialog.dart';
import 'package:frontend/app/modules/competition/presentation/widgets/competition_pagination_bar.dart';
import 'package:frontend/app/shared/extensions/context_extension.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/functions/format_amount.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/empty_state.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';

class MobileCompetitionPage extends ConsumerStatefulWidget {
  const MobileCompetitionPage({
    super.key,
    this.selectedCompetitionId,
    this.initialQuery = '',
    this.initialStatus = 'registration',
    this.initialOrdering = 'start_date',
    this.initialTab = 'discover',
    this.initialDiscoverPage = 1,
    this.initialMyPage = 1,
    this.initialLeaderboardPage = 1,
    this.initialPageSize = 20,
  });

  final int? selectedCompetitionId;
  final String initialQuery;
  final String initialStatus;
  final String initialOrdering;
  final String initialTab;
  final int initialDiscoverPage;
  final int initialMyPage;
  final int initialLeaderboardPage;
  final int initialPageSize;

  @override
  ConsumerState<MobileCompetitionPage> createState() => _MobileCompetitionPageState();
}

enum _MobileCompetitionTab { discover, mine }

class _MobileCompetitionPageState extends ConsumerState<MobileCompetitionPage> {
  late _MobileCompetitionTab _tab;
  bool _isJoining = false;
  late final TextEditingController _searchController;
  Timer? _debounce;
  late String _statusFilter;
  late String _ordering;
  int? _selectedCompetitionId;
  late int _discoverPage;
  late int _myPage;
  late int _leaderboardPage;
  late int _pageSize;

  @override
  void initState() {
    super.initState();
    _tab = widget.initialTab == 'mine'
        ? _MobileCompetitionTab.mine
        : _MobileCompetitionTab.discover;
    _searchController = TextEditingController(text: widget.initialQuery);
    _statusFilter = widget.initialStatus;
    _ordering = widget.initialOrdering;
    _selectedCompetitionId = widget.selectedCompetitionId;
    _discoverPage = widget.initialDiscoverPage;
    _myPage = widget.initialMyPage;
    _leaderboardPage = widget.initialLeaderboardPage;
    _pageSize = widget.initialPageSize;
    Future.microtask(() async {
      await _syncFromRoute(forceReload: true);
      if (_selectedCompetitionId != null && mounted) {
        await _openCompetitionSheet(_selectedCompetitionId!, updateRoute: false);
      }
    });
  }

  @override
  void didUpdateWidget(covariant MobileCompetitionPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    final routeChanged = oldWidget.selectedCompetitionId != widget.selectedCompetitionId ||
        oldWidget.initialQuery != widget.initialQuery ||
        oldWidget.initialStatus != widget.initialStatus ||
        oldWidget.initialOrdering != widget.initialOrdering ||
        oldWidget.initialTab != widget.initialTab;

    if (routeChanged) {
      _tab = widget.initialTab == 'mine'
          ? _MobileCompetitionTab.mine
          : _MobileCompetitionTab.discover;
      _searchController.text = widget.initialQuery;
      _statusFilter = widget.initialStatus;
      _ordering = widget.initialOrdering;
      _selectedCompetitionId = widget.selectedCompetitionId;
      _discoverPage = widget.initialDiscoverPage;
      _myPage = widget.initialMyPage;
      _leaderboardPage = widget.initialLeaderboardPage;
      _pageSize = widget.initialPageSize;
      Future.microtask(() async {
        await _syncFromRoute(forceReload: true);
      });
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _syncFromRoute({bool forceReload = false}) async {
    await ref.read(competitionDiscoverProvider.notifier).load(
      query: _discoverQuery(),
      page: forceReload ? _discoverPage : null,
      pageSize: _pageSize,
    );
    if (isAuthenticated()) {
      await ref.read(competitionMyProvider.notifier).load(
        page: forceReload ? _myPage : null,
        pageSize: _pageSize,
      );
    }
    if (_selectedCompetitionId != null) {
      await ref.read(competitionDetailProvider.notifier).load(_selectedCompetitionId!);
      await ref
          .read(competitionLeaderboardProvider.notifier)
          .load(_selectedCompetitionId!, page: forceReload ? _leaderboardPage : null, pageSize: _pageSize);
    }
  }

  Map<String, String> _discoverQuery() {
    return {
      'status': _statusFilter,
      'ordering': _ordering,
      if (_searchController.text.trim().isNotEmpty) 'q': _searchController.text.trim(),
      if (_statusFilter == 'registration') 'registration_open': 'true',
    };
  }

  void _updateRoute({int? competitionId, String? tab}) {
    context.go(
      DashboardRoutes.competitionLocation(
        competitionId: competitionId?.toString() ?? _selectedCompetitionId?.toString(),
        query: _searchController.text,
        status: _statusFilter,
        ordering: _ordering,
        tab: tab ?? (_tab == _MobileCompetitionTab.mine ? 'mine' : 'discover'),
        discoverPage: '$_discoverPage',
        myPage: '$_myPage',
        leaderboardPage: '$_leaderboardPage',
        pageSize: '$_pageSize',
      ),
    );
  }

  void _applyFilters() {
    _selectedCompetitionId = null;
    _discoverPage = 1;
    _leaderboardPage = 1;
    _updateRoute(competitionId: null);
  }

  void _resetFilters() {
    setState(() {
      _tab = _MobileCompetitionTab.discover;
      _searchController.text = '';
      _statusFilter = 'registration';
      _ordering = 'start_date';
      _selectedCompetitionId = null;
      _discoverPage = 1;
      _myPage = 1;
      _leaderboardPage = 1;
      _pageSize = 20;
    });
    _updateRoute(competitionId: null, tab: 'discover');
  }

  Future<void> _openCompetitionSheet(int competitionId, {bool updateRoute = true}) async {
    _selectedCompetitionId = competitionId;
    _leaderboardPage = 1;
    if (updateRoute) {
      _updateRoute(competitionId: competitionId);
    }
    await ref.read(competitionDetailProvider.notifier).load(competitionId);
    await ref.read(competitionLeaderboardProvider.notifier).load(competitionId, page: 1);

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

    final remainingCash =
        num.tryParse(result.data.remainingBbCashBalance) ?? 0;
    context.showSuccess(
      '${result.data.message} Remaining BB cash: ${formatAmount(remainingCash)}',
    );
    await _syncFromRoute();
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
          _selectedCompetitionId = created.id;
          _updateRoute(competitionId: created.id);
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
            TextField(
              controller: _searchController,
              style: TextStyle(color: colors.alwaysWhite),
              onChanged: (_) {
                _debounce?.cancel();
                _debounce = Timer(
                  const Duration(milliseconds: 600),
                  _applyFilters,
                );
              },
              onSubmitted: (_) {
                _debounce?.cancel();
                _applyFilters();
              },
              decoration: InputDecoration(
                hintText: 'Search competitions',
                hintStyle: TextStyle(color: colors.always8B949E),
                prefixIcon: Icon(Icons.search, color: colors.always8B949E),
                filled: true,
                fillColor: colors.always161B22,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: colors.always30363D),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: colors.always30363D),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: colors.always52AAFF),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _dropdown(
                    value: _statusFilter,
                    items: const {
                      'registration': 'Registration',
                      'active': 'Active',
                      'completed': 'Completed',
                      'cancelled': 'Cancelled',
                    },
                    onChanged: (value) {
                      if (value == null) return;
                      setState(() {
                        _statusFilter = value;
                      });
                      _applyFilters();
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _dropdown(
                    value: _ordering,
                    items: const {
                      'start_date': 'Start Date',
                      '-start_date': 'Latest Start',
                      'end_date': 'End Date',
                      '-created_at': 'Newest',
                    },
                    onChanged: (value) {
                      if (value == null) return;
                      setState(() {
                        _ordering = value;
                      });
                      _applyFilters();
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _dropdown(
                    value: '$_pageSize',
                    items: const {
                      '10': '10 / page',
                      '20': '20 / page',
                      '50': '50 / page',
                    },
                    onChanged: (value) {
                      if (value == null) return;
                      setState(() {
                        _pageSize = int.parse(value);
                        _discoverPage = 1;
                        _myPage = 1;
                        _leaderboardPage = 1;
                      });
                      _applyFilters();
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: CustomOutlinedButton.big(
                    text: 'Apply',
                    onTap: _applyFilters,
                    textColor: colors.alwaysE6EDF3,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: CustomOutlinedButton.big(
                    text: 'Reset',
                    onTap: _resetFilters,
                    textColor: colors.alwaysE6EDF3,
                  ),
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
                      _updateRoute(tab: 'discover');
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
                      _updateRoute(tab: 'mine');
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
                        onNext: () async {
                          final next = discoverState.isSuccess ? discoverState.data.next : null;
                          if (next == null) return;
                          _discoverPage = int.tryParse(Uri.parse(next).queryParameters['page'] ?? '') ?? _discoverPage;
                          _updateRoute();
                        },
                        onPrevious: () async {
                          final previous = discoverState.isSuccess ? discoverState.data.previous : null;
                          if (previous == null) return;
                          _discoverPage = int.tryParse(Uri.parse(previous).queryParameters['page'] ?? '') ?? _discoverPage;
                          _updateRoute();
                        },
                        onOpen: _openCompetitionSheet,
                        onJoin: _joinCompetition,
                        isJoining: _isJoining,
                      )
                    : _MyCompetitionMobileList(
                        state: myState,
                        currentPage: myNotifier.currentPage,
                        onNext: () async {
                          final next = myState.isSuccess ? myState.data.next : null;
                          if (next == null) return;
                          _myPage = int.tryParse(Uri.parse(next).queryParameters['page'] ?? '') ?? _myPage;
                          _updateRoute();
                        },
                        onPrevious: () async {
                          final previous = myState.isSuccess ? myState.data.previous : null;
                          if (previous == null) return;
                          _myPage = int.tryParse(Uri.parse(previous).queryParameters['page'] ?? '') ?? _myPage;
                          _updateRoute();
                        },
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

  Widget _dropdown({
    required String value,
    required Map<String, String> items,
    required ValueChanged<String?> onChanged,
  }) {
    final colors = ref.watch(appThemeProvider).colors;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: colors.always161B22,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.always30363D),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          dropdownColor: colors.always1F242C,
          isExpanded: true,
          style: TextStyle(color: colors.alwaysWhite, fontSize: 12),
          items: items.entries
              .map(
                (entry) => DropdownMenuItem<String>(
                  value: entry.key,
                  child: Text(entry.value),
                ),
              )
              .toList(),
          onChanged: onChanged,
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
                      '${item.memberCount}/${item.maxMembers} members • \$${item.entryFee}',
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
                                onPrevious: () async {
                                  await leaderboardNotifier.previousPage();
                                },
                                onNext: () async {
                                  await leaderboardNotifier.nextPage();
                                },
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
