import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class CustomCheckbox extends ConsumerWidget {
  final bool value;
  final VoidCallback onTap;

  const CustomCheckbox({
    super.key,
    required this.value,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(2),
      child: Container(
        width: 24,
        height: 24,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            width: value ? 1 : 2,
            color: value ? colors.alwaysWhite : colors.always8B949E,
          ),
          color: value ? colors.alwaysWhite : null,
        ),
        child: value
            ? Icon(
                Icons.check,
                size: 16,
                color: colors.alwaysBlack,
              )
            : null,
      ),
    );
  }
}
