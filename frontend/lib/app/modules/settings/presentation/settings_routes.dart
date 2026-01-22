import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/modules/settings/presentation/entries/account_entry.dart';
import 'package:frontend/app/modules/settings/presentation/entries/betting_preference_entry.dart';
import 'package:frontend/app/modules/settings/presentation/entries/notifications_entry.dart';
import 'package:frontend/app/modules/settings/presentation/entries/security_entry.dart';
import 'package:frontend/app/modules/settings/presentation/entries/settings_entry.dart';
import 'package:frontend/app/modules/settings/presentation/entries/wallet_transactions_entry.dart';
import 'package:frontend/app/shared/guards/is_authenticated_guard.dart';
import 'package:go_router/go_router.dart';

/// Workaround fix till i can figure out how to do this using the  [IsAuthenticatedGuard] class

bool _requiresAuth(String location) {
  final authPaths = [
    SettingsRoutes.settings,
    SettingsRoutes.account,
    SettingsRoutes.walletTransactions,
    SettingsRoutes.bettingPreference,
    SettingsRoutes.security,
    SettingsRoutes.notifications,
  ];

  return authPaths.any((path) => location.startsWith(path));
}

class SettingsRoutes {
  static const String settings = '/settings';

  static const String account = '$settings/account';
  static const String walletTransactions = '$settings/wallet-transactions';
  static const String bettingPreference = '$settings/betting-preference';
  static const String security = '$settings/security';
  static const String notifications = '$settings/notifications';

  static final values = <RouteBase>[
    StatefulShellRoute.indexedStack(
      builder: (context, state, navigationShell) {
        return SettingsEntry(shell: navigationShell);
      },

      /// Workaround fix till i can figure out how to do this using the  [IsAuthenticatedGuard] class

      redirect: (context, state) {
        // Get the container from context
        final container = ProviderScope.containerOf(context);
        final user = container.read(currentUserProvider);

        // Check if the route requires authentication
        final requiresAuth = _requiresAuth(state.uri.toString());

        if (requiresAuth && user == null) {
          return DashboardRoutes.trending;
        }

        return null; // No redirect needed
      },
      branches: [
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: account,
              builder: (context, state) => const AccountEntry(),
            ),
          ],
        ),

        //wallet transactions
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: walletTransactions,
              builder: (context, state) => const WalletTransactionsEntry(),
            ),
          ],
        ),

        //betting preference
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: bettingPreference,
              builder: (context, state) => const BettingPreferenceEntry(),
            ),
          ],
        ),

        //security
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: security,
              builder: (context, state) => const SecurityEntry(),
            ),
          ],
        ),

        //notifications
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: notifications,
              builder: (context, state) => const NotificationsEntry(),
            ),
          ],
        ),
      ],
    ),
  ];
}
