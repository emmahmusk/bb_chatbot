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
  static const Duration _marketRefreshInterval = Duration(seconds: 30);

  bool _isPredictionSlipOpen = false;
  Timer? _marketRefreshTimer;
  bool _isMarketRefreshInFlight = false;
  String? _persistedCompetitionId;

  @override
  void initState() {
    super.initState();
    _marketRefreshTimer = Timer.periodic(_marketRefreshInterval, (_) {
      _pollCurrentMarketBranch();
    });
  }

  @override
  void dispose() {
    _marketRefreshTimer?.cancel();
    super.dispose();
  }

  Future<Map<String, String>?> _currentMarketQueryParams() async {
    final prefs = await SharedPreferences.getInstance();

    switch (widget.shell.currentIndex) {
      case 0:
        return {
          'trending': 'true',
          'page': prefs.getString('trendingPage') ?? '1',
        };
      case 2:
        return {
          'expiring_soon': 'true',
          'page': prefs.getString('expiringSoonPage') ?? '1',
        };
      case 3:
        return {
          'page': prefs.getString('allStocksPage') ?? '1',
        };
      default:
        return null;
    }
  }

  Future<void> _pollCurrentMarketBranch() async {
    if (_isMarketRefreshInFlight) {
      return;
    }

    final queryParams = await _currentMarketQueryParams();
    if (queryParams == null) {
      return;
    }

    _isMarketRefreshInFlight = true;
    try {
      await ref.read(getMarketsProviderNew.notifier).get(
        queryParams: queryParams,
        preserveState: true,
        preserveOrder: true,
      );
    } finally {
      _isMarketRefreshInFlight = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final selectedStocks = ref.watch(selectedStockProvider);
    final routeUri = GoRouterState.of(context).uri;
    final myCompetitions = ref.watch(competitionMyProvider);
    final activeCompetitionId = routeUri.queryParameters['competitionId'];
    final isCompetitionPage = routeUri.path == DashboardRoutes.competitions;

    String? effectiveCompetitionId = activeCompetitionId;
    if ((effectiveCompetitionId == null || effectiveCompetitionId.isEmpty) &&
        isCompetitionPage &&
        myCompetitions.isSuccess &&
        myCompetitions.data.results.isNotEmpty) {
      effectiveCompetitionId =
          myCompetitions.data.results.first.competition.toString();
    }
    effectiveCompetitionId ??= _persistedCompetitionId;

    if (effectiveCompetitionId != null && effectiveCompetitionId.isNotEmpty) {
      _persistedCompetitionId = effectiveCompetitionId;
    }

    final isCompetitionMode =
        effectiveCompetitionId != null && effectiveCompetitionId.isNotEmpty;

    return SafeArea(
      child: Stack(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
                child: _MobileDashboardHeader(
                  effectiveCompetitionId: effectiveCompetitionId,
                  isCompetitionMode: isCompetitionMode,
                ),
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
                child: _MobileRouteChipHeader(
                  shell: widget.shell,
                  effectiveCompetitionId: effectiveCompetitionId,
                  isCompetitionMode: isCompetitionMode,
                  onExitCompetitionMode: () {
                    setState(() {
                      _persistedCompetitionId = null;
                    });
                    context.go(DashboardRoutes.trending);
                  },
                ),
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
      routeUri.queryParameters['competitionId'] ?? _persistedCompetitionId ?? '',
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
  const _MobileDashboardHeader({
    required this.effectiveCompetitionId,
    required this.isCompetitionMode,
  });

  final String? effectiveCompetitionId;
  final bool isCompetitionMode;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final profile = ref.watch(currentUserProvider);
    final myCompetitions = ref.watch(competitionMyProvider);
    final colors = ref.watch(appThemeProvider).colors;
    final competitionRouteId = effectiveCompetitionId;
    final selectedCompetitionId = int.tryParse(competitionRouteId ?? '');

    if (isCompetitionMode &&
        !myCompetitions.isLoading &&
        !myCompetitions.isSuccess) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(competitionMyProvider.notifier).load();
      });
    }

    String trendingRoute() {
      if (competitionRouteId == null || competitionRouteId.isEmpty) {
        return DashboardRoutes.trending;
      }
      return Uri(
        path: DashboardRoutes.trending,
        queryParameters: {'competitionId': competitionRouteId},
      ).toString();
    }

    String competitionsRoute() {
      if (competitionRouteId == null || competitionRouteId.isEmpty) {
        return DashboardRoutes.competitions;
      }
      return DashboardRoutes.competitionLocation(
        competitionId: competitionRouteId,
      );
    }

    String displayedCoinBalance = profile?.walletCoinBalance ?? '0.00';
    if (selectedCompetitionId != null && myCompetitions.isSuccess) {
      for (final membership in myCompetitions.data.results) {
        if (membership.competition == selectedCompetitionId) {
          displayedCoinBalance = membership.competitionCoinBalance;
          break;
        }
      }
    }
    final walletCoinBalance = formatAmount(
      double.tryParse(displayedCoinBalance) ?? 0.0,
    );

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
              onTap: () => context.go(competitionsRoute()),
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
    required this.effectiveCompetitionId,
    required this.isCompetitionMode,
    required this.onExitCompetitionMode,
  });

  final StatefulNavigationShell shell;
  final String? effectiveCompetitionId;
  final bool isCompetitionMode;
  final VoidCallback onExitCompetitionMode;

  @override
  ConsumerState<_MobileRouteChipHeader> createState() =>
      _MobileRouteChipHeaderState();
}

class _MobileRouteChipHeaderState
    extends ConsumerState<_MobileRouteChipHeader> {
  late bool _isMarketOpen;
  late Timer _timer;

  Future<void> _openMarketBranch({
    required String routePath,
    required String pagePreferenceKey,
    required Map<String, String> queryParams,
  }) async {
    final routeUri = GoRouterState.of(context).uri;
    final effectiveCompetitionId = widget.effectiveCompetitionId;

    final targetRoute =
        effectiveCompetitionId == null || effectiveCompetitionId.isEmpty
            ? routePath
            : Uri(
                path: routePath,
                queryParameters: {'competitionId': effectiveCompetitionId},
              ).toString();

    if (routeUri.toString() == targetRoute) {
      return;
    }

    ref.read(getMarketsProviderNew.notifier).showLoading();
    context.go(targetRoute);

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
        if (widget.isCompetitionMode)
          _RouteChip(
            label: 'Main Page',
            isActive: false,
            onTap: widget.onExitCompetitionMode,
            leadingIcon: Icons.arrow_back_rounded,
          ),
        _RouteChip(
          label: 'Trending Predictions',
          isActive: widget.shell.currentIndex == 0,
          onTap: () => _openMarketBranch(
            routePath: DashboardRoutes.trending,
            pagePreferenceKey: 'trendingPage',
            queryParams: const {'trending': 'true'},
          ),
        ),
        _RouteChip(
          label: 'Expiring Soon',
          isActive: widget.shell.currentIndex == 2,
          onTap: () => _openMarketBranch(
            routePath: DashboardRoutes.expiringSoon,
            pagePreferenceKey: 'expiringSoonPage',
            queryParams: const {'expiring_soon': 'true'},
          ),
        ),
        _RouteChip(
          label: 'All Stocks',
          isActive: widget.shell.currentIndex == 3,
          onTap: () => _openMarketBranch(
            routePath: DashboardRoutes.allStocks,
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
    this.leadingIcon,
  });

  final String label;
  final VoidCallback onTap;
  final bool isActive;
  final IconData? leadingIcon;

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
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (leadingIcon != null) ...[
              Icon(
                leadingIcon,
                size: 14,
                color: colors.alwaysWhite,
              ),
              const SizedBox(width: 6),
            ],
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
