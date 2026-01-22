import 'package:frontend/app/modules/dashboard/presentation/entries/all_bets_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/dashboard_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/expiring_soon_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/high_volume_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/tech_stocks_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/trending_entry.dart';
import 'package:go_router/go_router.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/stock_profile_page.dart';


class DashboardRoutes {
  static const String dashboard = '/dashboard';

  static const String trending = '$dashboard/trending';
  static const String expiringSoon = '$dashboard/expiring-soon';
  // static const String highVolume = '$dashboard/high-volume';
  // static const String techStocks = '$dashboard/tech-stocks';
  static const String allStocks = '$dashboard/all-stocks';
  static const String allBets = '$dashboard/all-bets';
  static const String stockProfile = '$dashboard/stock-profile';

  static final values = <RouteBase>[
    StatefulShellRoute.indexedStack(
      // redirect: [HasLoggedInGuard()].run,
      builder: (_, __, shell) => DashboardEntry(shell: shell),
      branches: [
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: trending,
              builder: (_, __) => TrendingEntry(),
            ),
          ],
        ),
        
        StatefulShellBranch(routes: 
        [
              GoRoute(
                path: stockProfile,
                builder: (context, state) {
                  final id = state.uri.queryParameters['id'] ?? '';
                  
                  return StockProfilePage(id: id );
                },
        ),
        ]
        ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: expiringSoon,
              builder: (_, __) => ExpiringSoonEntry(),
            ),
          ],
        ),
        // StatefulShellBranch(
        //   routes: [
        //     GoRoute(
        //       path: highVolume,
        //       builder: (_, __) => HighVolumeEntry(),
        //     ),
        //   ],
        // ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: allStocks,
              builder: (_, __) => TechStocksEntry(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: allBets,
              builder: (_, __) => AllBetsEntry(),
            ),
          ],
        ),
      ],
    ),
  ];
}
