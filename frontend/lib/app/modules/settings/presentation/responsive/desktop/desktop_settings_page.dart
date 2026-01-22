import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/svg.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/shared/classes/media/svgs.dart';
import 'package:frontend/app/shared/extensions/context_extension.dart';
import 'package:frontend/app/shared/extensions/list_extension.dart';
import 'package:frontend/app/shared/presentation/widgets/bull_bear_header.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';

class DesktopSettingsPage extends ConsumerStatefulWidget {
  const DesktopSettingsPage({
    super.key,
    required this.shell,
  });
  final StatefulNavigationShell shell;

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _DesktopSettingsPageState();
}

class _DesktopSettingsPageState extends ConsumerState<DesktopSettingsPage> {
  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final shell = widget.shell;
    return Scaffold(
      backgroundColor: colors.primary,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 20),
          BullBearHeader(shell: shell),
          const SizedBox(height: 20),
          CustomDivider(),
          const SizedBox(height: 20),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 140),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Clickable(
                  onClick: () {
                    context.go(DashboardRoutes.trending);
                  },
                  child: Row(
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
                          fontSize: 12,
                          color: colors.alwaysWhite,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Settings',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w500,
                    color: colors.alwaysWhite,
                  ),
                ),
                const SizedBox(height: 46),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 120),
              child: Row(
                children: [
                  LeftPane(
                    selectedTab: shell.currentIndex,
                    onTabChanged: (index) {
                      shell.goBranch(
                        index,
                        initialLocation: index == 0,
                      );
                      // final indexToAction = {
                      //   0: () => ref
                      //       .read(getJobsProvider("bank").notifier)
                      //       .getJobs(),
                      //   1: () => ref
                      //       .read(getJobsProvider("agency").notifier)
                      //       .getJobs(),
                      // };
                      // indexToAction[index]?.call();
                    },
                  ),
                  const SizedBox(width: 40),
                  Expanded(
                    flex: 3,
                    child: shell,
                  )
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class LeftPane extends ConsumerWidget {
  final ValueChanged<int> onTabChanged;
  final int selectedTab;
  const LeftPane({
    super.key,
    required this.selectedTab,
    required this.onTabChanged,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SizedBox(
      width: context.isDesktop ? 300 : 90,
      child: Container(
        padding: const EdgeInsets.all(8),
        child: Column(
          children: [
            for (final (i, item) in [
              (Svgs.account, "Account"),
              (Svgs.walletTransactions, "Wallet & Transaction"),
              (Svgs.bettingPreference, "Betting Preference"),
              (Svgs.security, "Security"),
              (Svgs.notifications, "Notifications"),
            ].enumerate()) ...[
              SideSelector(
                svg: item.$1,
                title: item.$2,
                selected: selectedTab == i,
                onTap: () {
                  onTabChanged(i);
                  // final func = {
                  //   0: () =>
                  //       ref.read(getStatsProvider.notifier).getStats(),
                  //   1: () {
                  //     ref
                  //         .read(getStaffPoolProvider("bank").notifier)
                  //         .get();
                  //     ref
                  //         .read(getJobsProvider("bank").notifier)
                  //         .getJobs();
                  //   },
                  //   2: () {
                  //     ref
                  //         .read(getStaffPoolProvider("agency").notifier)
                  //         .get();
                  //     ref
                  //         .read(getJobsProvider("agency").notifier)
                  //         .getJobs();
                  //     ref.read(getAgenciesProvider.notifier).get();
                  //   },
                  //   3: () {},
                  // };
                  // func[i]?.call();
                },
              ),
              const SizedBox(height: 16),
            ],
          ],
        ),
      ),
    );
  }
}

class SideSelector extends ConsumerWidget {
  final String svg;
  final String title;
  final bool selected;
  final VoidCallback? onTap;
  const SideSelector({
    super.key,
    required this.svg,
    required this.title,
    this.onTap,
    this.selected = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Clickable(
      onClick: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: selected ? colors.always1F242C : colors.transparent,
        ),
        child: Row(
          mainAxisAlignment: context.isDesktop
              ? MainAxisAlignment.start
              : MainAxisAlignment.center,
          children: [
            SvgPicture.asset(
              svg,
              colorFilter: ColorFilter.mode(
                colors.alwaysWhite,
                BlendMode.srcIn,
              ),
            ),
            if (context.isDesktop) ...[
              const SizedBox(width: 12),
              Text(
                title,
                style: TextStyle(
                  color: colors.alwaysWhite,
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const Spacer(),
              Icon(
                Icons.arrow_forward,
                color: colors.alwaysWhite,
                size: 16,
              ),
              const SizedBox(width: 12),
            ],
          ],
        ),
      ),
    );
  }
}
