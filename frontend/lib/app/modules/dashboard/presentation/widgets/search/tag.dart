import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class Tag extends ConsumerWidget {
  const Tag({
    super.key,
    required this.onClick,
    required this.text,
  });
  final VoidCallback onClick;
  final String text;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(100),
        color: colors.always1F242C,
      ),
      child: Clickable(
        onClick: onClick,
        child: Text(
          text,
          style: TextStyle(
            color: colors.alwaysE6EDF3,
            fontSize: 14,
            fontWeight: FontWeight.w400,
          ),
        ),
      ),
    );
  }
}
