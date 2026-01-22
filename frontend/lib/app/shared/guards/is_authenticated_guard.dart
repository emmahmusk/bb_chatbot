import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/shared/guards/route_guard.dart';
import 'package:go_router/go_router.dart';

class IsAuthenticatedGuard implements RouteGuard {
  BuildContext context;
  IsAuthenticatedGuard(this.context);
  @override
  String? run(GoRouterState state) {
    // Get the current provider container
    final container = ProviderScope.containerOf(
        GoRouter.of(context).routerDelegate.navigatorKey.currentContext!);

    // Read the current user from the provider
    final user = container.read(currentUserProvider);

    if (user == null) {
      return DashboardRoutes.trending;
    }
    return null;
  }
}
