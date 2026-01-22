import 'dart:math';

import 'package:flutter/material.dart';

extension ScreenSizeScaling on BuildContext {
  double scale(double value, {double baseScreenWidth = 1800.0}) {
    double screenWidth = maxWidth();
    double scaleFactor = screenWidth / baseScreenWidth;
    final toReturn = value * scaleFactor;

    return toReturn;
  }

  double scaleDown(double value) {
    double screenWidth = maxWidth();
    double scaleFactor = baseScreenWidth / screenWidth;
    final toReturn = value * scaleFactor;

    return toReturn;
  }

  double scalHeight(double value) {
    double screenWidth = maxHeight();
    double scaleFactor = screenWidth / baseScreenHeight;
    final toReturn = value * scaleFactor;
    return toReturn;
  }

  double scalHeightUp(double value) {
    double screenWidth = maxHeight();
    double scaleFactor = baseScreenHeight / screenWidth;
    final toReturn = value * scaleFactor;
    return toReturn;
  }

  double get baseScreenHeight {
    return 1041 - 5;
  }

  double get baseScreenWidth {
    return 1800 - 5;
  }

  double maxHeight() {
    return min(baseScreenHeight, MediaQuery.of(this).size.height);
  }

  double maxWidth() {
    return min(baseScreenWidth, MediaQuery.of(this).size.width);
  }

  double realMaxHeight() {
    return MediaQuery.of(this).size.height;
  }

  double realMaxWidth() {
    return MediaQuery.of(this).size.width;
  }

  double scaleC(
    double value, {
    double baseScreenWidth = 1800.0,
    double baseScreenHeight = 1126.0,
  }) {
    double screenWidth = MediaQuery.of(this).size.width;
    double screenHeight = MediaQuery.of(this).size.height;

    double widthScaleFactor = screenWidth / baseScreenWidth;
    double heightScaleFactor = screenHeight / baseScreenHeight;

    double scaleFactor = (widthScaleFactor + heightScaleFactor) /
        2; // Average of both scale factors

    return value * scaleFactor;
  }

  double scaleHeight(double value, {double baseScreenHeight = 1126.0}) {
    double screenHeight = MediaQuery.of(this).size.height;
    double scaleFactor = screenHeight / baseScreenHeight;
    return value * scaleFactor;
  }
}
