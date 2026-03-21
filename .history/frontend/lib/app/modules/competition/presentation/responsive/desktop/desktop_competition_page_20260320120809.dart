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
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/empty_state.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';

class DesktopCompetitionPage extends ConsumerStatefulWidget {
  const DesktopCompetitionPage({
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
  ConsumerState<DesktopCompetitionPage> createState() =>
      _DesktopCompetitionPageState();
}

enum _CompetitionTab { discover, myCompetitions }

class _DesktopCompetitionPageState extends ConsumerState<DesktopCompetitionPage> {
  late _CompetitionTab _activeTab;
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
    _activeTab = widget.initialTab == 'mine'
        ? _CompetitionTab.myCompetitions
        : _CompetitionTab.discover;
    _searchController = TextEditingController(text: widget.initialQuery);
    _statusFilter = widget.initialStatus;
    _ordering = widget.initialOrdering;
    _selectedCompetitionId = widget.selectedCompetitionId;
    _discoverPage = widget.initialDiscoverPage;
    _myPage = widget.initialMyPage;
    _leaderboardPage = widget.initialLeaderboardPage;
    _pageSize = widget.initialPageSize;
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
          if (item.endDate != null)
            Text(
              'Ends: ${_formatDate(item.endDate!)}',
              style: TextStyle(color: colors.alwaysE6EDF3, fontSize: 12),
            ),
          const SizedBox(height: 16),
          Row(
            children: [
              Text(
                'Leaderboard',
                style: TextStyle(
                  color: colors.alwaysWhite,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 12),
              ElevatedButton(
                onPressed: () => _showLeaderboardModal(context, leaderboardState, leaderboardCurrentPage, onLeaderboardNext, onLeaderboardPrevious),
                style: ElevatedButton.styleFrom(
                  backgroundColor: colors.always52AAFF,
                  foregroundColor: colors.alwaysWhite,
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: const Text('View Table'),
              ),
            ],
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

  String _joinLabel(CompetitionModel item) {
    if (item.userJoined) return 'Joined';
    if (item.isFull) return 'Full';
    if (!item.isRegistrationOpen) return 'Closed';
    return _isJoining ? 'Joining...' : 'Join';
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
        tab: tab ?? (_activeTab == _CompetitionTab.myCompetitions ? 'mine' : 'discover'),
        discoverPage: '$_discoverPage',
        myPage: '$_myPage',
        leaderboardPage: '$_leaderboardPage',
        pageSize: '$_pageSize',
      ),
    );
  }

  void _applyFilters() {
    setState(() {
      _selectedCompetitionId = null;
      _discoverPage = 1;
      _leaderboardPage = 1;
    });
    _updateRoute(competitionId: null);
  }

  void _resetFilters() {
    setState(() {
      _activeTab = _CompetitionTab.discover;
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

  bool _canJoin(CompetitionModel item) {
    return !item.userJoined && item.isRegistrationOpen && !item.isFull;
  }

  void _showLeaderboardModal(
    BuildContext context,
    AppState<PaginatedCompetitionLeaderboardModel> leaderboardState,
    int leaderboardCurrentPage,
    Future<void> Function() onLeaderboardNext,
    Future<void> Function() onLeaderboardPrevious,
  ) {
    final colors = ref.read(appThemeProvider).colors;
    showDialog(
      context: context,
      builder: (ctx) {
        if (leaderboardState.isInitial || leaderboardState.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (leaderboardState.isError) {
          return AlertDialog(
            title: const Text('Leaderboard'),
            content: Text(leaderboardState.errorMessage),
            actions: [TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Close'))],
          );
        }
        final rows = leaderboardState.data.results;
        return Dialog(
          backgroundColor: colors.always161B22,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Container(
            width: 700,
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Leaderboard', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.of(ctx).pop(),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                if (rows.isEmpty)
                  const Text('No participants yet.'),
                if (rows.isNotEmpty)
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const [
                        DataColumn(label: Text('Rank')),
                        DataColumn(label: Text('Username')),
                        DataColumn(label: Text('ROI')),
                        DataColumn(label: Text('P/L')),
                        DataColumn(label: Text('Total Bets')),
                        DataColumn(label: Text('Win Rate')),
                      ],
                      rows: [
                        for (int i = 0; i < rows.length; i++)
                          DataRow(cells: [
                            DataCell(Text('${rows[i].finalRank ?? (i + 1)}')),
                            DataCell(Text(rows[i].username)),
                            DataCell(Text('${rows[i].roi.toStringAsFixed(2)}%')),
                            DataCell(Text('${rows[i].netProfit.toStringAsFixed(2)}')),
                            DataCell(Text('${rows[i].totalBets}')),
                            DataCell(Text('${rows[i].winRate.toStringAsFixed(2)}%')),
                          ]),
                      ],
                    ),
                  ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    CompetitionPaginationBar(
                      currentPage: leaderboardCurrentPage,
                      hasPrevious: leaderboardState.data.previous != null,
                      hasNext: leaderboardState.data.next != null,
                      onPrevious: () async {
                        await onLeaderboardPrevious();
                      },
                      onNext: () async {
                        await onLeaderboardNext();
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _openCompetition(int competitionId) async {
    _selectedCompetitionId = competitionId;
    _leaderboardPage = 1;
    _updateRoute(competitionId: competitionId);
  }

  Future<void> _refreshData() async {
    await _syncFromRoute();
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
              Expanded(
                child: TextField(
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
              ),
              const SizedBox(width: 12),
              _filterDropdown(
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
              const SizedBox(width: 12),
              _filterDropdown(
                value: _ordering,
                items: const {
                  'start_date': 'Start Date',
                  '-start_date': 'Latest Start',
                  'end_date': 'End Date',
                  '-created_at': 'Newest',
                  'created_at': 'Oldest',
                },
                onChanged: (value) {
                  if (value == null) return;
                  setState(() {
                    _ordering = value;
                  });
                  _applyFilters();
                },
              ),
              const SizedBox(width: 12),
              _filterDropdown(
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
              const SizedBox(width: 12),
              CustomOutlinedButton.big(
                text: 'Apply',
                onTap: _applyFilters,
                textColor: colors.alwaysE6EDF3,
              ),
              const SizedBox(width: 12),
              CustomOutlinedButton.big(
                text: 'Reset',
                onTap: _resetFilters,
                textColor: colors.alwaysE6EDF3,
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
                  _updateRoute(tab: 'discover');
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
                  _updateRoute(tab: 'mine');
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
                      onDiscoverNext: () async {
                        final next = discoverState.isSuccess ? discoverState.data.next : null;
                        if (next == null) return;
                        _discoverPage = int.tryParse(Uri.parse(next).queryParameters['page'] ?? '') ?? _discoverPage;
                        _updateRoute();
                      },
                      onDiscoverPrevious: () async {
                        final previous = discoverState.isSuccess ? discoverState.data.previous : null;
                        if (previous == null) return;
                        _discoverPage = int.tryParse(Uri.parse(previous).queryParameters['page'] ?? '') ?? _discoverPage;
                        _updateRoute();
                      },
                      myState: myState,
                      myCurrentPage: myNotifier.currentPage,
                      onMyNext: () async {
                        final next = myState.isSuccess ? myState.data.next : null;
                        if (next == null) return;
                        _myPage = int.tryParse(Uri.parse(next).queryParameters['page'] ?? '') ?? _myPage;
                        _updateRoute();
                      },
                      onMyPrevious: () async {
                        final previous = myState.isSuccess ? myState.data.previous : null;
                        if (previous == null) return;
                        _myPage = int.tryParse(Uri.parse(previous).queryParameters['page'] ?? '') ?? _myPage;
                        _updateRoute();
                      },
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
                      onLeaderboardNext: () async {
                        final next = leaderboardState.isSuccess ? leaderboardState.data.next : null;
                        if (next == null) return;
                        _leaderboardPage = int.tryParse(Uri.parse(next).queryParameters['page'] ?? '') ?? _leaderboardPage;
                        _updateRoute();
                      },
                      onLeaderboardPrevious: () async {
                        final previous = leaderboardState.isSuccess ? leaderboardState.data.previous : null;
                        if (previous == null) return;
                        _leaderboardPage = int.tryParse(Uri.parse(previous).queryParameters['page'] ?? '') ?? _leaderboardPage;
                        _updateRoute();
                      },
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
                value: memberPercent.toDouble(),
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

  Widget _filterDropdown({
    required String value,
    required Map<String, String> items,
    required ValueChanged<String?> onChanged,
  }) {
    final colors = ref.watch(appThemeProvider).colors;

    return Container(
      width: 170,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: colors.always161B22,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.always30363D),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          isExpanded: true,
          dropdownColor: colors.always1F242C,
          style: TextStyle(color: colors.alwaysWhite, fontSize: 13),
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
