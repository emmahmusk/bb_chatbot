import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/shared/classes/media/svgs.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';

class MobileSettingsPage extends ConsumerWidget {
  const MobileSettingsPage({super.key, required this.shell});

  final StatefulNavigationShell shell;

  static const _items = <_SettingsNavItem>[
    _SettingsNavItem(index: 0, title: 'Account', svg: Svgs.account),
    _SettingsNavItem(index: 1, title: 'Wallet', svg: Svgs.walletTransactions),
    _SettingsNavItem(
      index: 2,
      title: 'Preferences',
      svg: Svgs.bettingPreference,
    ),
    _SettingsNavItem(index: 3, title: 'Security', svg: Svgs.security),
    _SettingsNavItem(index: 4, title: 'Notifications', svg: Svgs.notifications),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Clickable(
                  onClick: () => context.go(DashboardRoutes.trending),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.arrow_back,
                        color: colors.alwaysWhite,
                        size: 16,
                      ),
                      const SizedBox(width: 10),
                      Text(
                        'Go home',
                        style: TextStyle(
                          fontSize: 13,
                          color: colors.alwaysWhite,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Text(
                  'Settings',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w600,
                    color: colors.alwaysWhite,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Manage your account, wallet, and preferences with touch-friendly navigation.',
                  style: TextStyle(
                    fontSize: 14,
                    height: 1.5,
                    color: colors.always8B949E,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                for (final item in _items) ...[
                  _SettingsNavChip(
                    item: item,
                    isSelected: shell.currentIndex == item.index,
                    onTap: () => shell.goBranch(item.index),
                  ),
                  if (item != _items.last) const SizedBox(width: 12),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: Container(
              margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              decoration: BoxDecoration(
                color: colors.always161B22,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: colors.always30363D.withValues(alpha: 0.6),
                ),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: shell,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsNavChip extends ConsumerWidget {
  const _SettingsNavChip({
    required this.item,
    required this.isSelected,
    required this.onTap,
  });

  final _SettingsNavItem item;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Clickable(
      onClick: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: isSelected
              ? colors.alwaysWhite.withValues(alpha: 0.12)
              : colors.always30363D.withValues(alpha: 0.2),
          border: Border.all(
            color: isSelected ? colors.alwaysWhite : colors.always30363D,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SvgPicture.asset(
              item.svg,
              width: 18,
              height: 18,
              colorFilter: ColorFilter.mode(
                colors.alwaysWhite,
                BlendMode.srcIn,
              ),
            ),
            const SizedBox(width: 10),
            Text(
              item.title,
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

class _SettingsNavItem {
  const _SettingsNavItem({
    required this.index,
    required this.title,
    required this.svg,
  });

  final int index;
  final String title;
  final String svg;
}
