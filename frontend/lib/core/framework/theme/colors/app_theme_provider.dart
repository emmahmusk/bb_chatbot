import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app_theme.dart';

final appThemeProvider =
    StateNotifierProvider<AppThemeProvider, AppTheme>((ref) {
  return AppThemeProvider();
});

class AppThemeProvider extends StateNotifier<AppTheme> {
  AppThemeProvider() : super(AppTheme.light());

  void toggleTheme() {
    state = state.mode == ThemeMode.light ? AppTheme.dark() : AppTheme.light();
  }

  void setThemeFromBrightness(Brightness brightness) {
    if (brightness == Brightness.light) {
      state = AppTheme.light();
      return;
    }
    state = AppTheme.dark();
  }
}
