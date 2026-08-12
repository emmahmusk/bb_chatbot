import 'package:frontend/app/modules/dashboard/presentation/entries/all_bets_entry.dart';
import 'package:frontend/app/modules/competition/presentation/entries/competition_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/dashboard_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/expiring_soon_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/high_volume_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/stock_profile_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/tech_stocks_entry.dart';
import 'package:frontend/app/modules/dashboard/presentation/entries/trending_entry.dart';
import 'package:go_router/go_router.dart';


class DashboardRoutes {
  static const String dashboard = '/dashboard';

  static const String trending = '$dashboard/trending';
  static const String expiringSoon = '$dashboard/expiring-soon';
  // static const String highVolume = '$dashboard/high-volume';
  // static const String techStocks = '$dashboard/tech-stocks';
  static const String allStocks = '$dashboard/all-stocks';
  static const String competitions = '$dashboard/competitions';
  static const String allBets = '$dashboard/all-bets';
  static const String stockProfile = '$dashboard/stock-profile';

  static String competitionLocation({
    String? competitionId,
    String? query,
    String? status,
    String? ordering,
    String? tab,
    String? discoverPage,
    String? myPage,
    String? myStatus,
    String? leaderboardPage,
    String? pageSize,
  }) {
    final params = <String, String>{};
    if (competitionId != null && competitionId.isNotEmpty) {
      params['competitionId'] = competitionId;
    }
    if (query != null && query.trim().isNotEmpty) {
      params['q'] = query.trim();
    }
    if (status != null && status.trim().isNotEmpty) {
      params['status'] = status.trim();
    }
    if (ordering != null && ordering.trim().isNotEmpty) {
      params['ordering'] = ordering.trim();
    }
    if (tab != null && tab.trim().isNotEmpty) {
      params['tab'] = tab.trim();
    }
    if (discoverPage != null && discoverPage.trim().isNotEmpty) {
      params['discoverPage'] = discoverPage.trim();
    }
    if (myPage != null && myPage.trim().isNotEmpty) {
      params['myPage'] = myPage.trim();
    }
    if (myStatus != null && myStatus.trim().isNotEmpty) {
      params['myStatus'] = myStatus.trim();
    }
    if (leaderboardPage != null && leaderboardPage.trim().isNotEmpty) {
      params['leaderboardPage'] = leaderboardPage.trim();
    }
    if (pageSize != null && pageSize.trim().isNotEmpty) {
      params['pageSize'] = pageSize.trim();
    }

    return Uri(path: competitions, queryParameters: params.isEmpty ? null : params)
        .toString();
  }

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

                  return StockProfileEntry(id: id);
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
              path: competitions,
              builder: (_, state) => CompetitionEntry(
                selectedCompetitionId: int.tryParse(
                  state.uri.queryParameters['competitionId'] ?? '',
                ),
                initialQuery: state.uri.queryParameters['q'] ?? '',
                initialStatus:
                    state.uri.queryParameters['status'] ?? 'registration',
                initialOrdering:
                    state.uri.queryParameters['ordering'] ?? 'start_date',
                initialTab: state.uri.queryParameters['tab'] ?? 'discover',
                initialDiscoverPage: int.tryParse(
                      state.uri.queryParameters['discoverPage'] ?? '',
                    ) ??
                    1,
                initialMyPage: int.tryParse(
                      state.uri.queryParameters['myPage'] ?? '',
                    ) ??
                    1,
                initialMyStatus:
                    state.uri.queryParameters['myStatus'] ?? 'live',
                initialLeaderboardPage: int.tryParse(
                      state.uri.queryParameters['leaderboardPage'] ?? '',
                    ) ??
                    1,
                initialPageSize: int.tryParse(
                      state.uri.queryParameters['pageSize'] ?? '',
                    ) ??
                    20,
              ),
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
