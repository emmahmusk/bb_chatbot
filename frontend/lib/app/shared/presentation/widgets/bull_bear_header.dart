import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/create_account_dialog.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/profile_settings_dialog.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/modules/dashboard/presentation/widgets/search/search_dialog.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/profile_logo.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/app/shared/functions/format_amount.dart';
import 'package:frontend/app/modules/competition/presentation/providers/competition_my_provider.dart';
import 'package:go_router/go_router.dart';
import 'dart:async';
import 'package:flutter/material.dart';
class BullBearHeader extends ConsumerStatefulWidget {
  const BullBearHeader({super.key, required this.shell});
  final StatefulNavigationShell shell;

  @override
  ConsumerState<BullBearHeader> createState() => _BullBearHeaderState();
}

class _BullBearHeaderState extends ConsumerState<BullBearHeader> {

  late bool isOpen;
  late Timer _timer;

  

  // String walletBalance = '0.00';

@override
void initState() {
  super.initState();
  isOpen = isUSMarketOpenNow();

  // Load wallet balance
  // loadWalletBalance();

  // Re-check market open every minute
  _timer = Timer.periodic(const Duration(minutes: 1), (_) {
    final currentStatus = isUSMarketOpenNow();
    if (currentStatus != isOpen) {
      setState(() => isOpen = currentStatus);
    }
  });
}

// Future<void> loadWalletBalance() async {
//   final prefs = await SharedPreferences.getInstance();
//   final balance = prefs.getString('wallet_balance') ?? '0.00';
//   setState(() {
//     walletBalance = balance;
//   });
// }


bool isUSMarketOpenNow() {
  final now = DateTime.now().toUtc();
  final eastern = now.subtract(const Duration(hours: 4)); // EDT = UTC-4 (adjust for EST in winter)

  final isWeekday = eastern.weekday >= 1 && eastern.weekday <= 5;
  final isOpenHours = (eastern.hour > 9 || (eastern.hour == 9 && eastern.minute >= 30)) && eastern.hour < 16;

  return isWeekday && isOpenHours;
}

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  Widget _competitionButtonIcon() {
    return const Icon(
      Icons.emoji_events_outlined,
      size: 18,
      color: Colors.white,
    );
  }


  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final colors = ref.watch(appThemeProvider).colors;
    final profile = ref.watch(currentUserProvider);

    // Detect if on competition page
    final routeUri = GoRouterState.of(context).uri;
    final location = routeUri.toString();
    final selectedCompetitionId = int.tryParse(
      routeUri.queryParameters['competitionId'] ?? '',
    );
    final isCompetitionPage = location.contains('/dashboard/competitions');
    final isCompetitionMode = isCompetitionPage || selectedCompetitionId != null;

    String trendingRouteWithContext() {
      if (selectedCompetitionId == null) {
        return DashboardRoutes.trending;
      }
      return Uri(
        path: DashboardRoutes.trending,
        queryParameters: {'competitionId': '$selectedCompetitionId'},
      ).toString();
    }

    String formattedWalletCoinBalance;
    if (isCompetitionMode) {
      // Prefer the currently selected competition from route; fallback to first joined.
      final myCompetitions = ref.watch(competitionMyProvider);
      String compBalance = '0.00';
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

        if (selectedCompetitionBalance != null) {
          compBalance = selectedCompetitionBalance;
        } else {
          compBalance = myCompetitions.data.results.first.competitionCoinBalance;
        }
      }
      final parsed = double.tryParse(compBalance) ?? 0.0;
      formattedWalletCoinBalance = formatAmount(parsed);
    } else {
      final walletCoinBalance = profile?.walletCoinBalance ?? '0.00';
      final parsedWalletCoinBalance = double.tryParse(walletCoinBalance) ?? 0.0;
      formattedWalletCoinBalance = formatAmount(parsedWalletCoinBalance);
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 120),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Clickable(
            onClick: () => context.go(trendingRouteWithContext()),
            child: Image.asset(
              Pngs.bullbearLogo,
              width: 98,
              height: 47,
              fit: BoxFit.cover,
            ),
          ),
          const SizedBox(width: 24),
          CustomOutlinedButtonWithIcon(
            icon: _competitionButtonIcon(),
            text: 'Competitions',
            color: colors.alwaysWhite,
            onTap: () {
              context.go(DashboardRoutes.competitions);
            },
          ),
          const SizedBox(width: 12),
          CustomOutlinedButtonWithIcon(
            icon: Image.asset(
              Pngs.moon,
              width: 16,
              height: 16,
              fit: BoxFit.cover,
            ),
            text: isUSMarketOpenNow() ? 'Market open' : 'Market closed',
            color: colors.alwaysWhite,
            onTap: () {
              showDialog(
                context: context,
                builder: (context) {
                  return AlertDialog(
                    backgroundColor: const Color(0xFF1F242C),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    titlePadding: const EdgeInsets.only(top: 20, left: 24, right: 24),
                    title: const Column(
                      children: [
                        Text(
                          "US Market Hours",
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.white),
                        ),
                        SizedBox(height: 12),
                        Divider(color: Colors.white, thickness: 1),
                      ],
                    ),
                    contentPadding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
                    content: const Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          "The US stock market is open from:\n\n"
                          "🕘 - 9:30 AM to 4:00 PM\n"
                          "🗓️ - Monday to Friday\n"
                          "🌎 - Timezone: Eastern Time (ET)\n\n"
                          "Note: Times may vary slightly due to Daylight Saving Time (EDT/EST).",
                          style: TextStyle(color: Colors.white),
                        ),
                        SizedBox(height: 20),
                        Divider(color: Colors.white, thickness: 1),
                        SizedBox(height: 20),
                      ],
                    ),
                    actionsAlignment: MainAxisAlignment.center,
                    actions: [
                      OutlinedButton(
                        onPressed: () => Navigator.of(context).pop(),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Colors.white),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: const Text(
                          "OK",
                          style: TextStyle(color: Colors.white),
                        ),
                      ),
                    ],
                  );
                },
              );
            },
          ),
          const SizedBox(width: 24),
          Expanded(
            child: Clickable(
              onClick: () {
                context.go(trendingRouteWithContext());
                showCenterDialog(context, child: SearchDialog());
              },
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 12,
                ),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(50),
                  border: Border.all(
                    color: colors.always30363D,
                    width: 1,
                  ),
                  color: colors.always30363D.withValues(alpha: 0.2),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Image.asset(
                      Pngs.search,
                      width: 20,
                      height: 20,
                      fit: BoxFit.cover,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Search stocks or profiles',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w300,
                        color: colors.alwaysWhite.withValues(alpha: 0.4),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 24),
          // Wallet balance and profile at top right
          if (user != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: colors.always30363D.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(50),
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
                  const SizedBox(width: 8),
                  Text(
                    '$formattedWalletCoinBalance BBC',
                    style: TextStyle(
                      color: colors.alwaysWhite,
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            ProfileLogo(
              onClick: () {
                showTopRightDialog(
                  context,
                  child: ProfileSettingsDialog(),
                );
              },
            ),
          ] else ...[
            // Login / Signup for unauthenticated users
            Clickable(
              onClick: () => showCenterDialog(context, child: LoginDialog()),
              child: Container(
                height: 40,
                padding: const EdgeInsets.symmetric(horizontal: 18),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(50),
                  border: Border.all(color: colors.always30363D, width: 1),
                  color: colors.always30363D.withValues(alpha: 0.2),
                ),
                child: Center(
                  child: Text(
                    'Log in',
                    style: TextStyle(
                      color: colors.alwaysWhite,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Clickable(
              onClick: () => showCenterDialog(context, child: CreateAccountDialog()),
              child: Container(
                height: 40,
                padding: const EdgeInsets.symmetric(horizontal: 18),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(50),
                  gradient: LinearGradient(
                    colors: [colors.always2867DF, colors.alwaysE954F6],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Center(
                  child: Text(
                    'Sign up',
                    style: TextStyle(
                      color: colors.alwaysWhite,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
          ]
        ],
      ),
    );
  }
}