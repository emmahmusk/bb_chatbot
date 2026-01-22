import 'package:flutter/material.dart';

import 'app_colors.dart';

class AppTheme {
  final AppColors colors;
  final ThemeMode mode;

  const AppTheme._({
    required this.colors,
    required this.mode,
  });

  bool get isDarkMode {
    return mode == ThemeMode.dark;
  }

  Brightness get brightness {
    return mode == ThemeMode.dark ? Brightness.dark : Brightness.light;
  }

  factory AppTheme.light() {
    return const AppTheme._(
      mode: ThemeMode.light,
      colors: AppColors(),
    );
  }

  factory AppTheme.dark() {
    return const AppTheme._(
      mode: ThemeMode.dark,
      colors: AppColors(),
    );
  }
}
