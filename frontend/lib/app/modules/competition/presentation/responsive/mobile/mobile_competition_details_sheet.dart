import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/modules/competition/data/models/competition_models.dart';
import 'package:frontend/app/modules/competition/domain/repositories/competition_repository.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_detail_provider.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_leaderboard_provider.dart';
import 'package:frontend/app/modules/competition/presentation/widgets/competition_pagination_bar.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/shared/extensions/context_extension.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/functions/format_amount.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';

class MobileCompetitionDetailsSheet extends ConsumerStatefulWidget {
  const MobileCompetitionDetailsSheet({
    super.key,
    required this.pageSize,
    required this.onJoined,
  });

  final int pageSize;
  final Future<void> Function() onJoined;

  @override
  ConsumerState<MobileCompetitionDetailsSheet> createState() =>
      _MobileCompetitionDetailsSheetState();
}

class _MobileCompetitionDetailsSheetState
    extends ConsumerState<MobileCompetitionDetailsSheet> {
  bool _isJoining = false;

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final detailState = ref.watch(competitionDetailProvider);
    final leaderboardState = ref.watch(competitionLeaderboardProvider);
    final leaderboardNotifier =
        ref.read(competitionLeaderboardProvider.notifier);

    return Container(
      decoration: BoxDecoration(
        color: colors.always0D1117,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
        border: Border.all(color: colors.always30363D),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.88,
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
                    ? ListView(
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      detailState.data.name,
                                      style: TextStyle(
                                        color: colors.alwaysWhite,
                                        fontSize: 22,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      detailState.data.description ??
                                          'Competition details are shown below.',
                                      style: TextStyle(
                                        color: colors.always8B949E,
                                        height: 1.45,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 12),
                              IconButton(
                                onPressed: () => Navigator.of(context).pop(),
                                icon: Icon(
                                  Icons.close_rounded,
                                  color: colors.alwaysWhite,
                                ),
                                style: IconButton.styleFrom(
                                  backgroundColor: colors.always161B22,
                                  side: BorderSide(color: colors.always30363D),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: CustomOutlinedButton.big(
                                  text: 'View Table',
                                  onTap: () => _showLeaderboardSheet(context),
                                  textColor: colors.alwaysE6EDF3,
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: CustomButton(
                                  text: _primaryActionLabel(detailState.data),
                                  fontSize: 14,
                                  height: 48,
                                  onPressed: _primaryAction(detailState.data),
                                ),
                              ),
                            ],
                          ),
                          if (_hasPrizePool(detailState.data)) ...[
                            const SizedBox(height: 18),
                            Text(
                              'Prize Pool',
                              style: TextStyle(
                                color: colors.alwaysWhite,
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 12),
                            Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children: _buildPrizeCards(
                                detailState.data,
                                colors,
                              ),
                            ),
                          ],
                          const SizedBox(height: 18),
                          Text(
                            'Competition Snapshot',
                            style: TextStyle(
                              color: colors.alwaysWhite,
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 10,
                            runSpacing: 10,
                            children: [
                              _MetricCard(
                                label: 'Status',
                                value: _titleCase(detailState.data.status),
                                icon: Icons.flag_outlined,
                              ),
                              _MetricCard(
                                label: 'Members',
                                value:
                                    '${detailState.data.memberCount}/${detailState.data.maxMembers}',
                                icon: Icons.groups_outlined,
                              ),
                              _MetricCard(
                                label: 'Entry Fee',
                                value:
                                    '\$${_formatMoney(detailState.data.entryFee)}',
                                icon: Icons.payments_outlined,
                              ),
                              _MetricCard(
                                label: 'Starting Balance',
                                value:
                                    '${_formatMoney(detailState.data.startingCoinBalance)} BBC',
                                icon: Icons.account_balance_wallet_outlined,
                              ),
                              _MetricCard(
                                label: 'Scoring',
                                value: _titleCase(
                                  detailState.data.scoringMethod.replaceAll(
                                    '_',
                                    ' ',
                                  ),
                                ),
                                icon: Icons.query_stats_outlined,
                              ),
                              _MetricCard(
                                label: 'Access',
                                value: detailState.data.isPrivate
                                    ? 'Private'
                                    : 'Public',
                                icon: Icons.lock_outline_rounded,
                              ),
                            ],
                          ),
                          const SizedBox(height: 18),
                          Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: colors.always161B22,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: colors.always30363D),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Schedule',
                                  style: TextStyle(
                                    color: colors.alwaysWhite,
                                    fontSize: 15,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                _ScheduleRow(
                                  label: 'Registration Closes',
                                  value: _formatDateOrFallback(
                                    detailState.data.registrationCloseDate,
                                  ),
                                ),
                                _ScheduleRow(
                                  label: 'Starts',
                                  value: _formatDateOrFallback(
                                    detailState.data.startDate,
                                  ),
                                ),
                                _ScheduleRow(
                                  label: 'Ends',
                                  value: _formatDateOrFallback(
                                    detailState.data.endDate,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 18),
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  'Leaderboard',
                                  style: TextStyle(
                                    color: colors.alwaysWhite,
                                    fontSize: 16,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                              Text(
                                'Current standings',
                                style: TextStyle(
                                  color: colors.always8B949E,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          if (leaderboardState.isSuccess &&
                              leaderboardState.data.results.isNotEmpty) ...[
                            for (final row in leaderboardState.data.results)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 10),
                                child: _LeaderboardRowCard(row: row),
                              ),
                            CompetitionPaginationBar(
                              currentPage: leaderboardNotifier.currentPage,
                              hasPrevious:
                                  leaderboardState.data.previous != null,
                              hasNext: leaderboardState.data.next != null,
                              onPrevious: () async {
                                await leaderboardNotifier.previousPage();
                              },
                              onNext: () async {
                                await leaderboardNotifier.nextPage();
                              },
                            ),
                          ] else if (leaderboardState.isLoading)
                            const Padding(
                              padding: EdgeInsets.symmetric(vertical: 32),
                              child: Center(child: CircularProgressIndicator()),
                            )
                          else if (leaderboardState.isError)
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              child: Text(
                                leaderboardState.errorMessage,
                                style: TextStyle(
                                  color: colors.alwaysFF4C4C,
                                ),
                              ),
                            )
                          else
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: colors.always161B22,
                                borderRadius: BorderRadius.circular(14),
                                border:
                                    Border.all(color: colors.always30363D),
                              ),
                              child: Text(
                                'No leaderboard data yet. Rankings will appear once members begin trading in this competition.',
                                style: TextStyle(
                                  color: colors.always8B949E,
                                  height: 1.4,
                                ),
                              ),
                            ),
                        ],
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

  bool _hasPrizePool(CompetitionModel item) {
    return (double.tryParse(item.firstPlacePrize) ?? 0) > 0 ||
        (double.tryParse(item.secondPlacePrize) ?? 0) > 0 ||
        (double.tryParse(item.thirdPlacePrize) ?? 0) > 0;
  }

  List<Widget> _buildPrizeCards(
    CompetitionModel item,
    dynamic colors,
  ) {
    final prizes = <Widget>[];

    void addPrize({
      required String label,
      required String amount,
      required IconData icon,
      required Color accent,
    }) {
      if ((double.tryParse(amount) ?? 0) <= 0) {
        return;
      }

      prizes.add(
        SizedBox(
          width: 136,
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: colors.always161B22,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: colors.always30363D),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, color: accent, size: 20),
                const SizedBox(height: 10),
                Text(
                  label,
                  style: TextStyle(
                    color: colors.always8B949E,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '\$${_formatMoney(amount)}',
                  style: TextStyle(
                    color: colors.alwaysWhite,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    addPrize(
      label: '1st Place',
      amount: item.firstPlacePrize,
      icon: Icons.emoji_events,
      accent: Colors.amber,
    );
    addPrize(
      label: '2nd Place',
      amount: item.secondPlacePrize,
      icon: Icons.workspace_premium_rounded,
      accent: Colors.blueGrey.shade200,
    );
    addPrize(
      label: '3rd Place',
      amount: item.thirdPlacePrize,
      icon: Icons.military_tech_rounded,
      accent: Colors.brown.shade300,
    );

    return prizes;
  }

  String _formatMoney(String raw) {
    return formatAmount(num.tryParse(raw) ?? 0);
  }

  String _formatDateOrFallback(DateTime? date) {
    if (date == null) {
      return 'Not set';
    }

    final local = date.toLocal();
    final month = local.month.toString().padLeft(2, '0');
    final day = local.day.toString().padLeft(2, '0');
    final year = local.year.toString();
    final hour = local.hour.toString().padLeft(2, '0');
    final minute = local.minute.toString().padLeft(2, '0');
    return '$day/$month/$year $hour:$minute';
  }

  String _titleCase(String value) {
    return value
        .split(' ')
        .where((part) => part.isNotEmpty)
        .map(
          (part) =>
              '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
        )
        .join(' ');
  }

  String _primaryActionLabel(CompetitionModel item) {
    if (item.userJoined) {
      return 'Open Competition';
    }
    if (_isJoining) {
      return 'Joining...';
    }
    if (item.isFull) {
      return 'Competition Full';
    }
    if (!item.isRegistrationOpen) {
      return 'Registration Closed';
    }
    return 'Join Competition';
  }

  VoidCallback? _primaryAction(CompetitionModel item) {
    if (item.userJoined) {
      return () {
        Navigator.of(context).pop();
        context.go(
          Uri(
            path: DashboardRoutes.trending,
            queryParameters: {'competitionId': '${item.id}'},
          ).toString(),
        );
      };
    }

    if (_isJoining || item.isFull || !item.isRegistrationOpen) {
      return null;
    }

    return () => _joinCompetition(item);
  }

  Future<void> _joinCompetition(CompetitionModel item) async {
    if (!isAuthenticated()) {
      showCenterDialog(context, child: const LoginDialog());
      return;
    }

    setState(() {
      _isJoining = true;
    });

    final result = await ref
        .read(competitionRepositoryProvider)
        .joinCompetition(item.id);

    if (!mounted) {
      return;
    }

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

    await ref.read(competitionDetailProvider.notifier).load(item.id);
    await ref
        .read(competitionLeaderboardProvider.notifier)
        .load(item.id, page: 1, pageSize: widget.pageSize);
    await widget.onJoined();
  }

  void _showLeaderboardSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) {
        return Consumer(
          builder: (context, ref, _) {
            final colors = ref.watch(appThemeProvider).colors;
            final leaderboardState = ref.watch(competitionLeaderboardProvider);
            final leaderboardNotifier =
                ref.read(competitionLeaderboardProvider.notifier);

            return Container(
              decoration: BoxDecoration(
                color: colors.always0D1117,
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(22)),
                border: Border.all(color: colors.always30363D),
              ),
              child: SafeArea(
                top: false,
                child: SizedBox(
                  height: MediaQuery.of(context).size.height * 0.8,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
                    child: Column(
                      children: [
                        Container(
                          width: 44,
                          height: 4,
                          decoration: BoxDecoration(
                            color: colors.always30363D,
                            borderRadius: BorderRadius.circular(999),
                          ),
                        ),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                'Leaderboard Table',
                                style: TextStyle(
                                  color: colors.alwaysWhite,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            IconButton(
                              onPressed: () => Navigator.of(sheetContext).pop(),
                              icon: Icon(
                                Icons.close_rounded,
                                color: colors.alwaysWhite,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Expanded(
                          child: leaderboardState.isLoading
                              ? const Center(
                                  child: CircularProgressIndicator(),
                                )
                              : leaderboardState.isError
                                  ? Center(
                                      child: Text(
                                        leaderboardState.errorMessage,
                                        style: TextStyle(
                                          color: colors.alwaysFF4C4C,
                                        ),
                                        textAlign: TextAlign.center,
                                      ),
                                    )
                                  : leaderboardState.data.results.isEmpty
                                      ? Center(
                                          child: Text(
                                            'No leaderboard entries yet.',
                                            style: TextStyle(
                                              color: colors.always8B949E,
                                            ),
                                          ),
                                        )
                                      : SingleChildScrollView(
                                          scrollDirection: Axis.horizontal,
                                          child: Container(
                                            decoration: BoxDecoration(
                                              color: colors.always161B22,
                                              borderRadius:
                                                  BorderRadius.circular(16),
                                              border: Border.all(
                                                color: colors.always30363D,
                                              ),
                                            ),
                                            child: DataTableTheme(
                                              data: DataTableThemeData(
                                                headingRowColor:
                                                    WidgetStateProperty.all(
                                                  colors.always1F242C,
                                                ),
                                                dataRowColor:
                                                    WidgetStateProperty.all(
                                                  colors.always161B22,
                                                ),
                                                headingTextStyle: TextStyle(
                                                  color: colors.alwaysWhite,
                                                  fontSize: 13,
                                                  fontWeight: FontWeight.w700,
                                                ),
                                                dataTextStyle: TextStyle(
                                                  color: colors.alwaysE6EDF3,
                                                  fontSize: 13,
                                                  fontWeight: FontWeight.w600,
                                                ),
                                                dividerThickness: 1,
                                              ),
                                              child: DataTable(
                                                horizontalMargin: 16,
                                                columnSpacing: 24,
                                                columns: const [
                                                  DataColumn(
                                                    label: Text('Rank'),
                                                  ),
                                                  DataColumn(
                                                    label: Text('Username'),
                                                  ),
                                                  DataColumn(
                                                    label: Text('P/L'),
                                                  ),
                                                  DataColumn(
                                                    label: Text('ROI'),
                                                  ),
                                                  DataColumn(
                                                    label: Text('Win Rate'),
                                                  ),
                                                ],
                                                rows: [
                                                  for (int i = 0;
                                                      i <
                                                          leaderboardState.data
                                                              .results.length;
                                                      i++)
                                                    DataRow(
                                                      cells: [
                                                        DataCell(
                                                          Text(
                                                            '${leaderboardState.data.results[i].finalRank ?? (i + 1)}',
                                                          ),
                                                        ),
                                                        DataCell(
                                                          Text(
                                                            leaderboardState
                                                                .data
                                                                .results[i]
                                                                .username,
                                                          ),
                                                        ),
                                                        DataCell(
                                                          Text(
                                                            leaderboardState
                                                                .data
                                                                .results[i]
                                                                .netProfit
                                                                .toStringAsFixed(
                                                                  2,
                                                                ),
                                                          ),
                                                        ),
                                                        DataCell(
                                                          Text(
                                                            '${leaderboardState.data.results[i].roi.toStringAsFixed(2)}%',
                                                          ),
                                                        ),
                                                        DataCell(
                                                          Text(
                                                            '${leaderboardState.data.results[i].winRate.toStringAsFixed(2)}%',
                                                          ),
                                                        ),
                                                      ],
                                                    ),
                                                ],
                                              ),
                                            ),
                                          ),
                                        ),
                        ),
                        if (leaderboardState.isSuccess)
                          CompetitionPaginationBar(
                            currentPage: leaderboardNotifier.currentPage,
                            hasPrevious:
                                leaderboardState.data.previous != null,
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
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }
}

class _MetricCard extends ConsumerWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return SizedBox(
      width: 136,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: colors.always161B22,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.always30363D),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: colors.always52AAFF, size: 18),
            const SizedBox(height: 10),
            Text(
              label,
              style: TextStyle(
                color: colors.always8B949E,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              value,
              style: TextStyle(
                color: colors.alwaysWhite,
                fontSize: 15,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ScheduleRow extends ConsumerWidget {
  const _ScheduleRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color: colors.always8B949E,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: TextStyle(
                color: colors.alwaysE6EDF3,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LeaderboardRowCard extends ConsumerWidget {
  const _LeaderboardRowCard({
    required this.row,
  });

  final CompetitionLeaderboardEntry row;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    final rank = row.finalRank ?? 0;
    final profitColor =
        row.netProfit >= 0 ? colors.always27D07F : colors.alwaysFF4C4C;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colors.always161B22,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.always30363D),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: colors.always1F242C,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: colors.always30363D),
                ),
                child: Text(
                  rank > 0 ? '$rank' : '-',
                  style: TextStyle(
                    color: colors.alwaysWhite,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  row.username,
                  style: TextStyle(
                    color: colors.alwaysWhite,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _MiniStat(
                  label: 'ROI',
                  value: '${row.roi.toStringAsFixed(2)}%',
                  valueColor: colors.always52AAFF,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _MiniStat(
                  label: 'P/L',
                  value: row.netProfit.toStringAsFixed(2),
                  valueColor: profitColor,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _MiniStat(
                  label: 'Win Rate',
                  value: '${row.winRate.toStringAsFixed(2)}%',
                  valueColor: colors.alwaysWhite,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniStat extends ConsumerWidget {
  const _MiniStat({
    required this.label,
    required this.value,
    required this.valueColor,
  });

  final String label;
  final String value;
  final Color valueColor;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      decoration: BoxDecoration(
        color: colors.always0D1117,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.always30363D),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: colors.always8B949E,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(
              color: valueColor,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
