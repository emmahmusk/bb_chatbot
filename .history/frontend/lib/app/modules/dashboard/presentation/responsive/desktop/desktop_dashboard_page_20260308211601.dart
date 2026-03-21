import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/get_bet_list_provider.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/sections/dashboard/bet_slip_section.dart';
import 'package:frontend/app/shared/presentation/widgets/bull_bear_header.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/get_markets_provider_new.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import '../../providers/bet_history_provider_new.dart';
import 'package:shared_preferences/shared_preferences.dart';
class DesktopDashboardPage extends ConsumerStatefulWidget {
  const DesktopDashboardPage({super.key, required this.shell});
  final StatefulNavigationShell shell;

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _DesktopDashboardPageState();
}

class _DesktopDashboardPageState extends ConsumerState<DesktopDashboardPage> {
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    return Scaffold(
      backgroundColor: colors.primary,
      body: Column(
        mainAxisSize: MainAxisSize.max,
         
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 10),
          BullBearHeader(shell: widget.shell),
          const SizedBox(height: 20),
          const CustomDivider(),
          const SizedBox(height: 20),
          CustomRouteChipHeader(
            currentIndex: widget.shell.currentIndex,
            onClick: (index) {
              widget.shell.goBranch(index);
              ref.read(betListProvider.notifier).state = [];
              setState(() {});
            },
          ),
          const SizedBox(height: 32),
          Expanded(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Expanded(
                  flex: 3,
                  child: widget.shell,
                ),
                const SizedBox(width: 24),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 40),
                    child: BetSlipSection(),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}

class CustomRouteChipHeader extends ConsumerWidget {
  const CustomRouteChipHeader({
    super.key,
    required this.currentIndex,
    required this.onClick,
  });
  final int currentIndex;
  final Function(int) onClick;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        mainAxisSize: MainAxisSize.max,
        children: [
          // Left group: Trending, Expiring Soon, All Stocks
          Expanded(
            flex: 7,
            child: Wrap(
              alignment: WrapAlignment.center,
              spacing: 10,
              runSpacing: 8,
              children: [
                // Trending
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () async {
                      // ✅ Get saved trending page from SharedPreferences (default = '1')
                      final prefs = await SharedPreferences.getInstance();
                      final savedPage = prefs.getString('trendingPage') ?? '1';

                      // ✅ Call the API with the saved page number
                      ref.read(getMarketsProviderNew.notifier).get(
                        queryParams: {
                          'trending': 'true',
                          'page': savedPage,
                        },
                      );

                      // ✅ Navigate to the trending page
                      context.go('/dashboard/trending');
                    },

                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
                      decoration: BoxDecoration(
                        border: Border.all(color: colors.alwaysWhite),
                        borderRadius: BorderRadius.circular(50),
                        color: colors.alwaysWhite.withOpacity(0.1),
                      ),
                      child: Text(
                        'Trending Predictions',
                        style: TextStyle(
                          color: colors.alwaysWhite,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ),
            
                // Expiring Soon
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () async{
                      // ✅ Get saved page from SharedPreferences (default = '1')
                      final prefs = await SharedPreferences.getInstance();
                      final savedPage = prefs.getString('expiringSoonPage') ?? '1';

                      // ✅ Call API with the saved page and expiring_soon=true
                      ref.read(getMarketsProviderNew.notifier).get(
                        queryParams: {
                          'expiring_soon': 'true',
                          'page': savedPage,
                        },
                      );
                       context.go('/dashboard/expiring-soon');
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
                      decoration: BoxDecoration(
                        border: Border.all(color: colors.alwaysWhite),
                        borderRadius: BorderRadius.circular(50),
                        color: colors.alwaysWhite.withOpacity(0.1),
                      ),
                      child: Text(
                        'Expiring Soon',
                        style: TextStyle(
                          color: colors.alwaysWhite,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ),
            
                // All Stocks
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () async {
                        // ✅ Get saved All Stocks page (default to '1' if none found)
                        final prefs = await SharedPreferences.getInstance();
                        final savedPage = prefs.getString('allStocksPage') ?? '1';

                        // ✅ Call the provider with the saved page
                        ref.read(getMarketsProviderNew.notifier).get(
                          queryParams: {
                            'page': savedPage,
                          },
                        );

                        // ✅ Navigate to All Stocks page
                        context.go('/dashboard/all-stocks');
                      },

                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
                      decoration: BoxDecoration(
                        border: Border.all(color: colors.alwaysWhite),
                        borderRadius: BorderRadius.circular(50),
                        color: colors.alwaysWhite.withOpacity(0.1),
                      ),
                      child: Text(
                        'All Stocks',
                        style: TextStyle(
                          color: colors.alwaysWhite,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Right-aligned: My Predictions
          Expanded(
              flex: 3,
              child: Align(
                alignment: Alignment.centerRight,
                child: MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                      onTap: () async {
                        if (!isAuthenticated()) {
                          showCenterDialog(context, child: const LoginDialog());
                          return;
                        }
                    
                        ref.read(betHistoryProvider.notifier).get();
                        context.go('/dashboard/all-bets');
                      },
                      child:  Container(
                          padding: const EdgeInsets.only(top: 6,bottom:6,left:20, right: 12),
                          decoration: BoxDecoration(
                            border: Border.all(color: colors.alwaysWhite),
                            borderRadius: BorderRadius.circular(50),
                            color: colors.alwaysWhite.withOpacity(0.1),
                          ),
                          child: Text(
                            'My Predictions',
                            style: TextStyle(
                              color: colors.alwaysWhite,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                     
                ),
              ),
            ),
           
          
        ],
      ),
    );
  }
}

