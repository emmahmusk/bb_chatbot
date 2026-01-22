import 'package:flutter/material.dart';
import 'package:frontend/app/shared/functions/alert_functions.dart';
import 'package:go_router/go_router.dart';

extension Extras on BuildContext {
  void showSuccess(String message) {
    showTopRightAlert(this, message, false);
  }

  void popShowError(String message) {
    pop(this);
    showError(message);
  }

  void showError(
    String message, {
    Duration duration = const Duration(seconds: 2),
  }) {
    showTopRightAlert(
      this,
      message,
      true,
      duration,
    );
  }

  bool get isMobile {
    return MediaQuery.of(this).size.width < 1050;
  }

  bool get isTablet {
    return MediaQuery.of(this).size.width < 1240.0 && !isMobile;
  }

  bool get isDesktop {
    return !isMobile && !isTablet;
  }
}
