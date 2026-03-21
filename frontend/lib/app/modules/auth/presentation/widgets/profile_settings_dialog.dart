import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/settings/presentation/settings_routes.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/functions/format_amount.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/app/shared/presentation/widgets/profile_logo.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
 class ProfileSettingsDialog extends ConsumerStatefulWidget {
  const ProfileSettingsDialog({super.key});

  @override
  ConsumerState<ProfileSettingsDialog> createState() => _ProfileSettingsDialogState();
}

class _ProfileSettingsDialogState extends ConsumerState<ProfileSettingsDialog> {
  String walletBalance = '0.00';
  String walletCoinBalance = '0.00';

  @override
  void initState() {
    super.initState();
    loadWalletBalance();
  }

  Future<void> loadWalletBalance() async {
    final prefs = await SharedPreferences.getInstance();
    final cashBalance = prefs.getString('wallet_balance') ?? '0.00';
    final coinBalance = prefs.getString('wallet_coin_balance') ?? '0.00';

    setState(() {
      walletBalance = cashBalance;
      walletCoinBalance = coinBalance;
    });
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final parsedWalletBalance = double.tryParse(walletBalance) ?? 0.0;
    final parsedWalletCoinBalance = double.tryParse(walletCoinBalance) ?? 0.0;
    final formattedWalletBalance = formatAmount(parsedWalletBalance);
    final formattedWalletCoinBalance = formatAmount(parsedWalletCoinBalance);

    return Container(
      width: 350,
      decoration: BoxDecoration(
        color: colors.always1F242C,
        borderRadius: BorderRadius.circular(16),
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Wallet Balances',
                      style: TextStyle(
                        fontWeight: FontWeight.w400,
                        fontSize: 14,
                        color: colors.always8B949E,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Container(
                          width: 28,
                          height: 28,
                          decoration: BoxDecoration(
                            color: colors.always27D07F.withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Center(
                            child: Icon(
                              Icons.attach_money_rounded,
                              size: 18,
                              color: colors.always27D07F,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '$formattedWalletBalance BB Cash',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w500,
                            color: colors.alwaysWhite,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Container(
                          width: 28,
                          height: 28,
                          decoration: BoxDecoration(
                            color: colors.alwaysFFD33D.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Center(
                            child: Image.asset(
                              Pngs.bullbearLogo,
                              width: 14,
                              height: 14,
                              fit: BoxFit.cover,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '$formattedWalletCoinBalance BBC',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w500,
                            color: colors.alwaysFFD33D,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Stack(
                clipBehavior: Clip.none,
                children: [
                  ProfileLogo(
                    onClick: () {},
                  ),
                  Positioned(
                    right: 1,
                    bottom: -30,
                    top: 0,
                    child: Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        color: colors.always27D07F,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          CustomDivider(),
          const SizedBox(height: 16),
          ProfileSettingsItem(
            asset: Pngs.settings,
            text: "Settings",
            onClick: () {
              context.go(SettingsRoutes.account);
            },
          ),
          const SizedBox(height: 16),
          ProfileSettingsItem(
            asset: Pngs.help,
            text: "Help",
            onClick: () {},
          ),
          const SizedBox(height: 16),
          CustomDivider(),
          const SizedBox(height: 16),
          ProfileSettingsItem(
            asset: Pngs.logout,
            text: "Logout",
            onClick: () {
              logout(context, ref);
            },
            hasTrailing: false,
          ),
        ],
      ),
    );
  }
}

class ProfileSettingsItem extends ConsumerWidget {
  const ProfileSettingsItem({
    super.key,
    required this.asset,
    required this.text,
    required this.onClick,
    this.hasTrailing = true,
  });
  final Function() onClick;
  final String asset;
  final String text;
  final bool hasTrailing;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Clickable(
      onClick: onClick,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Image.asset(
            asset,
            height: 16,
            width: 16,
            fit: BoxFit.cover,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: hasTrailing ? colors.alwaysWhite : colors.alwaysFF4C4C,
              ),
            ),
          ),
          if (hasTrailing)
            Icon(
              Icons.arrow_forward,
              size: 14,
              color: colors.alwaysWhite,
            ),
        ],
      ),
    );
  }
}
