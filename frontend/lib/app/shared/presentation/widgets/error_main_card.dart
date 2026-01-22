import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/main_card.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class ErrorMainCard extends ConsumerWidget {
  final String message;
  final VoidCallback? onReload;
  final Color? color;
  const ErrorMainCard({
    super.key,
    this.message = "Retry",
    this.onReload,
    this.color,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return MainCard(
      color: color,
      child: Column(
        children: [
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: colors.alwaysWhite,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CustomButton(
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 10,
                ),
                text: message,
                onPressed: onReload,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
