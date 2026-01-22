import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/svg.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class CloseIcon extends ConsumerWidget {
  final String svg;
  final VoidCallback? onTap;
  const CloseIcon({
    super.key,
    required this.svg,
    this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Clickable(
      onClick: onTap,
      child: Container(
        width: 24,
        height: 24,
        padding: const EdgeInsets.all(5),
        decoration: BoxDecoration(
          color: colors.transparent,
          shape: BoxShape.circle,
          border: Border.all(color: colors.alwaysWhite, width: 1.7),
        ),
        child: SvgPicture.asset(
          svg,
          color: colors.alwaysWhite,
        ),
      ),
    );
  }
}
