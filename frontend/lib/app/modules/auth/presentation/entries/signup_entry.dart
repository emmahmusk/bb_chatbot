import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/responsive/desktop/pages/desktop_signup_page.dart';
import 'package:frontend/app/modules/auth/presentation/responsive/mobile/pages/mobile_signup_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class SignupEntry extends ConsumerWidget {
  const SignupEntry({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ResponsiveBuilder(
      mobileBuilder: (context) => const MobileSignupPage(),
      desktopBuilder: (context) => const DesktopSignupPage(),
    );
  }
}
