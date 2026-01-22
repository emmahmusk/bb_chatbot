import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/modules/four_0_four/four_0_four_page.dart';
import 'package:frontend/app/modules/settings/presentation/settings_routes.dart';
import 'package:go_router/go_router.dart';

final router = GoRouter(
  initialLocation: DashboardRoutes.trending,
  errorBuilder: (context, state) {
    /// 404 page for web
    /// for mobile, this will be handled by the MaterialApp onUnknownRoute
    return Four0FourPage();
  },
  routes: [
    // ...AuthRoutes.values,
    ...DashboardRoutes.values,
    ...SettingsRoutes.values,
    // Add more routes here
  ],
);
