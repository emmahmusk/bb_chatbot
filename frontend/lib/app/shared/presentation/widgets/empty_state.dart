import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:frontend/app/shared/classes/media/svgs.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class EmptyState extends ConsumerWidget {
  final String title;
  final String message;
  final ({
    String buttonText,
    VoidCallback onButtonPressed,
  })? button;
  const EmptyState({
    super.key,
    required this.message,
    required this.title,
    this.button,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SvgPicture.asset(
            Svgs.emptyState,
            width: 170,
            height: 170,
          ),
          const SizedBox(height: 10),
          Text(
            title,
            style: TextStyle(
              fontSize: 20,
              color: colors.alwaysWhite,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: colors.always8B949E,
              fontWeight: FontWeight.w400,
            ),
          ),
          if (button != null) ...[
            const SizedBox(height: 20),
            IntrinsicWidth(
              child: CustomButton(
                text: button!.buttonText,
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                onPressed: button!.onButtonPressed,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
