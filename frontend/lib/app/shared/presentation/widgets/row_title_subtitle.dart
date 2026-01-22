import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class RowTitleSubtitle extends ConsumerWidget {
  const RowTitleSubtitle({
    super.key,
    required this.title,
    required this.subtitle,
    this.titleColor,
    this.subtitleColor,
    this.titleSize,
    this.subtitleSize,
  });
  final String title;
  final String subtitle;
  final Color? titleColor;
  final Color? subtitleColor;
  final double? titleSize;
  final double? subtitleSize;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Expanded(
          child: Text(
            "$title:",
            style: TextStyle(
              fontSize: titleSize ?? 12,
              fontWeight: FontWeight.w500,
              color: titleColor ?? colors.alwaysWhite,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          subtitle,
          style: TextStyle(
            fontSize: subtitleSize ?? 12,
            fontWeight: FontWeight.w500,
            color: subtitleColor ?? colors.alwaysWhite,
          ),
        ),
      ],
    );
  }
}
