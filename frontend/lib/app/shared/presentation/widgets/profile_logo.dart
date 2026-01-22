import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ProfileLogo extends ConsumerStatefulWidget {
  final Function() onClick;

  const ProfileLogo({
    super.key,
    required this.onClick,
  });

  @override
  ConsumerState<ProfileLogo> createState() => _ProfileLogoState();
}

class _ProfileLogoState extends ConsumerState<ProfileLogo> {
  String initial = 'U';

  @override
  void initState() {
    super.initState();
    _loadInitialFromPrefs();
  }

  Future<void> _loadInitialFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    final fullName = prefs.getString('full_name');

    if (fullName != null && fullName.trim().isNotEmpty) {
      setState(() {
        initial = fullName.trim()[0].toUpperCase();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    const double size = 48.0;
    const double borderWidth = 1.33;

    return Clickable(
      onClick: widget.onClick,
      child: Container(
        width: size,
        height: size,
        decoration: const BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF2867DF),
              Color(0xFFE954F6),
            ],
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(borderWidth),
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: colors.primary,
            ),
            alignment: Alignment.center,
            child: Text(
              initial,
              style: TextStyle(
                fontSize: 16,
                color: colors.alwaysWhite,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
