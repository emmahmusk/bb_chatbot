import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class MainCard extends ConsumerWidget {
  final Widget child;
  final EdgeInsets? padding;
  final Color? color;
  final double? width;
  final double? radius;
  const MainCard({
    super.key,
    required this.child,
    this.padding,
    this.color,
    this.width,
    this.radius,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Container(
      width: width,
      padding: padding ??
          const EdgeInsets.symmetric(
            horizontal: 13,
            vertical: 18,
          ),
      decoration: BoxDecoration(
        color: color ?? colors.transparent,
        borderRadius: BorderRadius.circular(radius ?? 10),
        // border: Border.all(
        //   color: colors.alwaysE2E2E2,
        // ),
      ),
      child: child,
    );
  }
}

class DynamicWidthMainCard extends ConsumerWidget {
  const DynamicWidthMainCard({
    super.key,
    required this.child,
    this.onTap,
    this.padding,
    this.width,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final double? width;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appTheme = ref.watch(appThemeProvider);
    final colors = appTheme.colors;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: width,
        padding: padding ?? const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: colors.primary,
          borderRadius: BorderRadius.circular(10),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.09),
              blurRadius: 20,
              offset: const Offset(3, 3),
            ),
          ],
        ),
        child: child,
      ),
    );
  }
}
