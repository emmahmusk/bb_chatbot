import 'package:flutter/material.dart';
import 'package:frontend/app/modules/auth/presentation/responsive/desktop/pages/desktop_login_page.dart';
import 'package:frontend/app/modules/auth/presentation/responsive/mobile/pages/mobile_login_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class LoginEntry extends StatelessWidget {
  const LoginEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (_) => const MobileLoginPage(),
      desktopBuilder: (_) => const DesktopLoginPage(),
    );
  }
}
