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


  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);

    final colors = ref.watch(appThemeProvider).colors;
    final profile = ref.watch(currentUserProvider);
    final walletCoinBalance = profile?.walletCoinBalance ?? '0.00';
    final parsedWalletCoinBalance = double.tryParse(walletCoinBalance) ?? 0.0;
    // Use thousand separator formatting
    String formattedWalletCoinBalance = formatAmount(parsedWalletCoinBalance);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 120),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Clickable(
            onClick: () => context.go(DashboardRoutes.trending),
            child: Image.asset(
              Pngs.bullbearLogo,
              width: 98,
              height: 47,
              fit: BoxFit.cover,
            ),
          ),
          const Spacer(),
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
                context.go('/dashboard/trending');
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
          if (user == null) ...[
            CustomOutlinedButton.big(
              text: 'Log in',
              onTap: () {
                showCenterDialog(
                  context,
                  child: LoginDialog(),
                );
              },
            ),
            const SizedBox(width: 8),
            CustomButton(
              text: 'Get Started',
              height: 44,
              width: 120,
              fontSize: 12,
              borderRadius: 50,
              validator: () => true,
              onPressed: () {
                showCenterDialog(
                  context,
                  child: CreateAccountDialog(),
                );
              },
            ),
          ] else ...[
            CustomOutlinedButtonWithIcon(
              text: '$formattedWalletCoinBalance BBC',
              fontSize: 14,
              color: colors.alwaysWhite,
              icon: Container(
                width: 20,
                height: 20,
                decoration: BoxDecoration(
                  color: colors.alwaysFFD33D.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Center(
                  child: Image.asset(
                    Pngs.bullbearLogo,
                    width: 12,
                    height: 12,
                    fit: BoxFit.cover,
                  ),
                ),
              ),
              iconPosition: IconPosition.left,
              onTap: () {},
            ),

            const SizedBox(width: 24),
            ProfileLogo(
              onClick: () {
                showTopRightDialog(
                  context,
                  child: ProfileSettingsDialog(),
                );
              },
            ),
          ],
        ],
      ),
    );
  }
}