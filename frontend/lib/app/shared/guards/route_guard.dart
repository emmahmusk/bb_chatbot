import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

abstract interface class RouteGuard {
  String? run(GoRouterState state);
}

extension Run on List<RouteGuard> {
  String? run(BuildContext context, GoRouterState state) {
    for (final guard in this) {
      final result = guard.run(state);
      if (result != null) {
        return result;
      }
    }
    return null;
  }
}
