import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

void showTopRightAlert(BuildContext context, String message, bool isError,
    [Duration duration = const Duration(seconds: 2)]) {
  OverlayEntry overlayEntry = OverlayEntry(
    builder: (context) => Positioned(
      top: 10.0,
      right: 10.0,
      child: Material(
        elevation: 1.0,
        borderRadius: BorderRadius.circular(5.0),
        child: Consumer(
          builder: (context, ref, _) {
            final colors = ref.watch(appThemeProvider).colors;
            return Container(
              padding: const EdgeInsets.symmetric(
                vertical: 15.0,
                horizontal: 30,
              ),
              decoration: BoxDecoration(
                color: isError ? colors.alwaysEB0000 : colors.primary,
                borderRadius: BorderRadius.circular(5.0),
              ),
              child: Text(
                message,
                style: const TextStyle(color: Colors.white),
              ),
            );
          },
        ),
      ),
    ),
  );

  Overlay.of(context).insert(overlayEntry);

  Future.delayed(duration, () {
    overlayEntry.remove();
  });
}
