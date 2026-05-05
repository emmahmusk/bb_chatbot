import 'dart:ui';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/create_account_dialog.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/profile_settings_dialog.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_my_provider.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/get_markets_provider_new.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/stock_selection_provider.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/sections/dashboard/bet_slip_section.dart';
import 'package:frontend/app/modules/dashboard/presentation/widgets/search/search_dialog.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/functions/format_amount.dart';
import 'package:frontend/app/shared/functions/market_hours.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../providers/bet_history_provider_new.dart';

class MobileDashboardPage extends ConsumerStatefulWidget {
  const MobileDashboardPage({
    super.key,
    required this.shell,
  });

  final StatefulNavigationShell shell;

  @override
  ConsumerState<MobileDashboardPage> createState() =>
      _MobileDashboardPageState();
}

class _MobileDashboardPageState extends ConsumerState<MobileDashboardPage> {
  bool _isPredictionSlipOpen = false;

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final selectedStocks = ref.watch(selectedStockProvider);

    return SafeArea(
      child: Stack(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
                child: const _MobileDashboardHeader(),
              ),
              const SizedBox(height: 18),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Divider(
                  color: colors.always30363D,
                  height: 1,
                ),
              ),
              const SizedBox(height: 18),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: _MobileRouteChipHeader(shell: widget.shell),
              ),
              const SizedBox(height: 18),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 88),
                  child: widget.shell,
                ),
              ),
            ],
          ),
          Positioned(
            left: 16,
            right: 16,
            bottom: 16,
            child: Clickable(
              onClick: () => _openPredictionSlip(context),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  gradient: LinearGradient(
                    colors: [colors.always2867DF, colors.alwaysE954F6],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: colors.always2867DF.withValues(alpha: 0.25),
                      blurRadius: 24,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    Image.asset(
                      Pngs.wallet,
                      width: 18,
                      height: 18,
                      fit: BoxFit.cover,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        selectedStocks.isEmpty
                            ? 'Open Prediction Slip'
                            : 'Prediction Slip (${selectedStocks.length})',
                        style: TextStyle(
                          color: colors.alwaysWhite,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    Icon(
                      Icons.keyboard_arrow_up_rounded,
                      color: colors.alwaysWhite,
                      size: 24,
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (_isPredictionSlipOpen)
            Positioned.fill(
              child: IgnorePointer(
                child: ClipRect(
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
                    child: Container(
                      color: Colors.black.withValues(alpha: 0.36),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _openPredictionSlip(BuildContext context) async {
    if (_isPredictionSlipOpen) {
      return;
    }

    final routeUri = GoRouterState.of(context).uri;
    final competitionId = int.tryParse(
      routeUri.queryParameters['competitionId'] ?? '',
    );

    setState(() {
      _isPredictionSlipOpen = true;
    });

    try {
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        barrierColor: Colors.transparent,
        builder: (sheetContext) {
          return FractionallySizedBox(
            heightFactor: 0.88,
            child: SafeArea(
              top: false,
              child: Column(
                children: [
                  const SizedBox(height: 8),
                  Container(
                    width: 44,
                    height: 5,
                    decoration: BoxDecoration(
                      color: Colors.white38,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Expanded(
                    child: BetSlipSection(
                      competitionId: competitionId,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      );
    } finally {
      if (mounted) {
        setState(() {
          _isPredictionSlipOpen = false;
        });
      }
    }
  }
}

class _MobileDashboardHeader extends ConsumerWidget {
  const _MobileDashboardHeader();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final profile = ref.watch(currentUserProvider);
    final myCompetitions = ref.watch(competitionMyProvider);
    final colors = ref.watch(appThemeProvider).colors;
    final routeUri = GoRouterState.of(context).uri;
    final selectedCompetitionId = int.tryParse(
      routeUri.queryParameters['competitionId'] ?? '',
    );
    final isCompetitionPage = routeUri.path == DashboardRoutes.competitions;
    final isCompetitionMode =
        isCompetitionPage || selectedCompetitionId != null;

    if (isCompetitionMode &&
        !myCompetitions.isLoading &&
        !myCompetitions.isSuccess) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(competitionMyProvider.notifier).load();
      });
    }

    String trendingRoute() {
      if (selectedCompetitionId == null || isCompetitionPage) {
        return DashboardRoutes.trending;
      }
      return Uri(
        path: DashboardRoutes.trending,
        queryParameters: {'competitionId': '$selectedCompetitionId'},
      ).toString();
    }

    String walletCoinBalance = '0.00';
    if (isCompetitionMode) {
      String competitionBalance = '0.00';

      if (myCompetitions.isSuccess && myCompetitions.data.results.isNotEmpty) {
        String? selectedCompetitionBalance;

        if (selectedCompetitionId != null) {
          for (final membership in myCompetitions.data.results) {
            if (membership.competition == selectedCompetitionId) {
              selectedCompetitionBalance = membership.competitionCoinBalance;
              break;
            }
          }
        }

        competitionBalance = selectedCompetitionBalance ??
            myCompetitions.data.results.first.competitionCoinBalance;
      }

      walletCoinBalance = formatAmount(
        double.tryParse(competitionBalance) ?? 0.0,
      );
    } else if (profile != null) {
      walletCoinBalance = formatAmount(
        double.tryParse(profile.walletCoinBalance) ?? 0.0,
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Clickable(
                onClick: () => context.go(trendingRoute()),
                child: Image.asset(
                  Pngs.bullbearLogo,
                  width: 96,
                  height: 46,
                  fit: BoxFit.contain,
                  alignment: Alignment.centerLeft,
                ),
              ),
            ),
            const SizedBox(width: 12),
            _HeaderActionPill(
              label: 'Competitions',
              icon: Icons.emoji_events_outlined,
              onTap: () => context.go(DashboardRoutes.competitions),
            ),
          ],
        ),
        const SizedBox(height: 14),
        Clickable(
          onClick: () {
            context.go(trendingRoute());
            showCenterDialog(context, child: SearchDialog());
          },
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: colors.always30363D,
                width: 1,
              ),
              color: colors.always30363D.withValues(alpha: 0.2),
            ),
            child: Row(
              children: [
                Image.asset(
                  Pngs.search,
                  width: 18,
                  height: 18,
                  fit: BoxFit.cover,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Search stocks or profiles',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w300,
                      color: colors.alwaysWhite.withValues(alpha: 0.45),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        if (user != null)
          Row(
            children: [
              Expanded(
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  decoration: BoxDecoration(
                    color: colors.always30363D.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: colors.always30363D, width: 1),
                  ),
                  child: Row(
                    children: [
                      Image.asset(
                        Pngs.wallet,
                        width: 18,
                        height: 18,
                        fit: BoxFit.cover,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          '$walletCoinBalance BBC',
                          style: TextStyle(
                            color: colors.alwaysWhite,
                            fontWeight: FontWeight.w600,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Clickable(
                onClick: () {
                  showCenterDialog(
                    context,
                    child: const ProfileSettingsDialog(),
                  );
                },
                child: Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: colors.always30363D, width: 1),
                    color: colors.always30363D.withValues(alpha: 0.2),
                  ),
                  child: const Icon(
                    Icons.person_outline,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          )
        else
          Row(
            children: [
              Expanded(
                child: _AuthActionPill(
                  label: 'Log in',
                  filled: false,
                  onTap: () => showCenterDialog(
                    context,
                    child: const LoginDialog(),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _AuthActionPill(
                  label: 'Sign up',
                  filled: true,
                  onTap: () => showCenterDialog(
                    context,
                    child: const CreateAccountDialog(),
                  ),
                ),
              ),
            ],
          ),
      ],
    );
  }
}

class _MobileRouteChipHeader extends ConsumerStatefulWidget {
  const _MobileRouteChipHeader({
    required this.shell,
  });

  final StatefulNavigationShell shell;

  @override
  ConsumerState<_MobileRouteChipHeader> createState() =>
      _MobileRouteChipHeaderState();
}

class _MobileRouteChipHeaderState
    extends ConsumerState<_MobileRouteChipHeader> {
  late bool _isMarketOpen;
  late Timer _timer;

  Future<void> _openMarketBranch({
    required int index,
    required String pagePreferenceKey,
    required Map<String, String> queryParams,
  }) async {
    if (widget.shell.currentIndex == index) {
      return;
    }

    ref.read(getMarketsProviderNew.notifier).showLoading();
    widget.shell.goBranch(index);

    final prefs = await SharedPreferences.getInstance();
    final savedPage = prefs.getString(pagePreferenceKey) ?? '1';

    await ref.read(getMarketsProviderNew.notifier).get(
      queryParams: {
        ...queryParams,
        'page': savedPage,
      },
    );
  }

  @override
  void initState() {
    super.initState();
    _isMarketOpen = isUsMarketOpenNow();
    _timer = Timer.periodic(const Duration(minutes: 1), (_) {
      final currentStatus = isUsMarketOpenNow();
      if (currentStatus != _isMarketOpen && mounted) {
        setState(() {
          _isMarketOpen = currentStatus;
        });
      }
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;

    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        _RouteChip(
          label: 'Trending Predictions',
          isActive: widget.shell.currentIndex == 0,
          onTap: () => _openMarketBranch(
            index: 0,
            pagePreferenceKey: 'trendingPage',
            queryParams: const {'trending': 'true'},
          ),
        ),
        _RouteChip(
          label: 'Expiring Soon',
          isActive: widget.shell.currentIndex == 2,
          onTap: () => _openMarketBranch(
            index: 2,
            pagePreferenceKey: 'expiringSoonPage',
            queryParams: const {'expiring_soon': 'true'},
          ),
        ),
        _RouteChip(
          label: 'All Stocks',
          isActive: widget.shell.currentIndex == 3,
          onTap: () => _openMarketBranch(
            index: 3,
            pagePreferenceKey: 'allStocksPage',
            queryParams: const {},
          ),
        ),
        _RouteChip(
          label: 'My Predictions',
          isActive: widget.shell.currentIndex == 5,
          onTap: () async {
            if (!isAuthenticated()) {
              showCenterDialog(context, child: const LoginDialog());
              return;
            }
            await ref.read(betHistoryProvider.notifier).get();
            if (!context.mounted) return;
            widget.shell.goBranch(5);
          },
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: colors.always30363D),
            color: colors.always30363D.withValues(alpha: 0.2),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.circle,
                size: 10,
                color: _isMarketOpen ? Colors.greenAccent : Colors.orangeAccent,
              ),
              const SizedBox(width: 8),
              Text(
                _isMarketOpen ? 'Market open' : 'Market closed',
                style: TextStyle(
                  color: colors.alwaysWhite,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _HeaderActionPill extends ConsumerWidget {
  const _HeaderActionPill({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Clickable(
      onClick: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: colors.always30363D),
          color: colors.always30363D.withValues(alpha: 0.2),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: colors.alwaysWhite),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: colors.alwaysWhite,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AuthActionPill extends ConsumerWidget {
  const _AuthActionPill({
    required this.label,
    required this.onTap,
    required this.filled,
  });

  final String label;
  final VoidCallback onTap;
  final bool filled;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Clickable(
      onClick: onTap,
      child: Container(
        height: 46,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border:
              filled ? null : Border.all(color: colors.always30363D, width: 1),
          color: filled ? null : colors.always30363D.withValues(alpha: 0.2),
          gradient: filled
              ? LinearGradient(
                  colors: [colors.always2867DF, colors.alwaysE954F6],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              color: colors.alwaysWhite,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }
}

class _RouteChip extends ConsumerWidget {
  const _RouteChip({
    required this.label,
    required this.onTap,
    required this.isActive,
  });

  final String label;
  final VoidCallback onTap;
  final bool isActive;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Clickable(
      onClick: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: isActive ? colors.alwaysWhite : colors.always30363D,
          ),
          color: isActive
              ? colors.alwaysWhite.withValues(alpha: 0.1)
              : colors.always30363D.withValues(alpha: 0.2),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: colors.alwaysWhite,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}
