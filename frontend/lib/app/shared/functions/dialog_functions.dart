import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/extensions/context_extension.dart';
import 'package:frontend/app/shared/extensions/size_extension.dart';
import 'package:frontend/app/shared/functions/ui_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/bullbear_logo.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';

Future<void> showRightDialog(BuildContext context, {required Widget child}) {
  return showDialog(
    context: context,
    barrierDismissible: true,
    builder: (context) {
      return Consumer(
        builder: (context, ref, _) {
          return Dialog(
            alignment: Alignment.centerRight,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
            child: SizedBox(
              width: 594,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(child: child),
                ],
              ),
            ),
          );
        },
      );
    },
  );
}

Future<void> showBottomDialog(
  BuildContext context, {
  required Widget child,
  bool setToBottom = true,
  bool barrierDismissible = true,
}) {
  return showDialog(
    context: context,
    barrierDismissible: barrierDismissible,
    builder: (context) {
      return Consumer(
        builder: (context, ref, _) {
          final colors = ref.watch(appThemeProvider).colors;
          return Dialog(
            alignment: setToBottom ? Alignment.bottomCenter : Alignment.center,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
            insetPadding: EdgeInsets.symmetric(
              horizontal: context.scale(250),
              vertical: 100,
            ),
            backgroundColor: colors.primary,
            child: child,
          );
        },
      );
    },
  );
}

Future<void> showLoadingDialog(
  BuildContext context,
) {
  hideKeyBoard();
  return showDialog(
    context: context,
    barrierDismissible: false,
    builder: (context) {
      return Dialog(
        backgroundColor: Colors.transparent,
        elevation: 0,
        child: BullBearLogo.mid(),
      );
    },
  );
}

Future<void> showSuccessDialog(
  BuildContext context, {
  String? title,
  String? message,
  VoidCallback? onClosed,
}) {
  hideKeyBoard();
  return showBottomDialog(
    context,
    barrierDismissible: false,
    child: Container(),
  );
}

Future<void> showErrorDialog(
  BuildContext context, {
  String? title,
  String? message,
  VoidCallback? onClosed,
}) {
  hideKeyBoard();
  return showBottomDialog(
    context,
    barrierDismissible: false,
    child: Container(),
  );
}

Future<void> popAndShowErrorDialog(
  BuildContext context, {
  String? title,
  String? message,
  VoidCallback? onClosed,
}) {
  pop(context);
  return showErrorDialog(
    context,
    title: title,
    message: message,
    onClosed: onClosed,
  );
}

Future<void> popAndShowSuccessDialog(
  BuildContext context, {
  String? title,
  String? message,
  VoidCallback? onClosed,
}) {
  pop(context);
  return showSuccessDialog(
    context,
    title: title,
    message: message,
    onClosed: onClosed,
  );
}

Future<void> popAndShowErrorDialogAndPopAgainOnClosed(
  BuildContext context, {
  String? title,
  String? message,
  VoidCallback? onClosed,
}) {
  pop(context);
  return showErrorDialog(
    context,
    title: title,
    message: message,
    onClosed: () {
      pop(context);
      onClosed?.call();
    },
  );
}

Future<void> popDualAndShowSuccessDialog(
  BuildContext context, {
  String? title,
  String? message,
  VoidCallback? onClosed,
}) {
  pop(context);
  return showSuccessDialog(
    context,
    title: title,
    message: message,
    onClosed: () {
      pop(context);
      onClosed?.call();
    },
  );
}

Future<T?> showCenterDialog<T>(
  BuildContext context, {
  required Widget child,
}) {
  return showDialog<T>(
    context: context,
    barrierColor: Colors.transparent,
    barrierDismissible: true,
    builder: (dialogContext) {
      return Consumer(
        builder: (context, ref, _) {
          final colors = ref.watch(appThemeProvider).colors;
          final isMobile = context.isMobile;
          return Stack(
            children: [
              Positioned.fill(
                child: GestureDetector(
                   behavior: HitTestBehavior.opaque, // Ensures taps are detected
                    onTap: () => Navigator.of(context).pop(), // Dismiss on tap outside
                  child: BackdropFilter(
                    filter: ImageFilter.blur(
                      sigmaX: 8.0,
                      sigmaY: 5.0,
                    ),
                    child: Container(
                      color: colors.alwaysBlack.withValues(alpha: 0),
                    ),
                  ),
                ),
              ),
              Center(
                child: Dialog(
                  insetPadding: EdgeInsets.symmetric(
                    horizontal: isMobile ? 16 : 100,
                    vertical: isMobile ? 20 : 80,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  elevation: 0,
                  backgroundColor: colors.alwaysWhite,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      child,
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      );
    },
  );
}

Future<T?> showTopRightDialog<T>(
  BuildContext context, {
  required Widget child,
  bool barrierDismissible = true,
  double topOffset = 74,
  double rightOffset = 45,
  double width = 350,
}) {
  hideKeyBoard();

  return showDialog<T>(
    context: context,
    barrierColor: Colors.transparent,
    barrierDismissible: false, // Disable Flutter's default dismiss
    builder: (dialogContext) {
      return Consumer(builder: (ctx, ref, _) {
        final colors = ref.watch(appThemeProvider).colors;

        return Stack(
          children: [
            // Background blur + manual dismiss tap handler
            Positioned.fill(
              child: GestureDetector(
                onTap: () {
                  if (barrierDismissible) {
                    Navigator.of(dialogContext).pop();
                  }
                },
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 8.0, sigmaY: 5.0),
                  child: Container(
                    color: Colors.transparent, // Must be fully transparent
                  ),
                ),
              ),
            ),

            // The actual dialog, padded into top‑right
            Padding(
              padding: EdgeInsets.only(
                top: topOffset,
                right: rightOffset,
              ),
              child: Align(
                alignment: Alignment.topRight,
                child: Material(
                  color: Colors.transparent,
                  child: Container(
                    width: width,
                    decoration: BoxDecoration(
                      color: colors.primary,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: child,
                  ),
                ),
              ),
            ),
          ],
        );
      });
    },
  );
}

