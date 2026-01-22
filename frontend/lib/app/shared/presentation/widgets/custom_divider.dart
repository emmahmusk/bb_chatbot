import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

enum CustomDividerType { vertical, horizontal }

class CustomDivider extends ConsumerWidget {
  final CustomDividerType type;
  final Color? color;
  const CustomDivider({
    super.key,
    this.type = CustomDividerType.horizontal,
    this.color,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    const factor = 1.7;
    return Container(
      width: type == CustomDividerType.horizontal ? double.maxFinite : factor,
      height: type == CustomDividerType.horizontal ? factor : double.maxFinite,
      color: color ?? colors.always30363D,
    );
  }
}
