import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class TitleSubtitle extends ConsumerWidget {
  const TitleSubtitle({
    super.key,
    required this.title,
    required this.subtitle,
    this.crossAxisAlignment = CrossAxisAlignment.center,
  });
  final String title;
  final String subtitle;
  final CrossAxisAlignment crossAxisAlignment;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Column(
      crossAxisAlignment: crossAxisAlignment,
      children: [
        Text(
          title,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w600,
            color: colors.alwaysWhite,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: 12),
        Text(
          subtitle,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w400,
            color: colors.always8B949E,
            letterSpacing: 0,
          ),
        ),
      ],
    );
  }
}
