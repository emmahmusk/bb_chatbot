import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/extensions/context_extension.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class ResponsiveBuilder extends ConsumerWidget {
  final Widget Function(BuildContext context) mobileBuilder;
  final Widget Function(BuildContext context) desktopBuilder;
  final Widget Function(BuildContext context)? tabletBuilder;
  final bool hasScaffold;

  const ResponsiveBuilder({
    super.key,
    required this.mobileBuilder,
    required this.desktopBuilder,
    this.tabletBuilder,
    this.hasScaffold = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    late Widget child;
    if (context.isMobile) {
      child = mobileBuilder(context);
    } else if (context.isTablet) {
      if (tabletBuilder != null) {
        child = tabletBuilder!(context);
      } else {
        child = desktopBuilder(context);
      }
    } else {
      child = desktopBuilder(context);
    }
    if (hasScaffold) {
      final colors = ref.watch(appThemeProvider).colors;
      return Scaffold(
        body: child,
        backgroundColor: colors.primary,
      );
    }
    return child;
  }
}
