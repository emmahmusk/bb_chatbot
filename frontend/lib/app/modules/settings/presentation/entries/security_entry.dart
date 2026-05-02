import 'package:flutter/widgets.dart';
import 'package:frontend/app/modules/settings/presentation/responsive/desktop/desktop_security_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class SecurityEntry extends StatelessWidget {
  const SecurityEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (_) => DesktopSecurityPage(),
      desktopBuilder: (_) => DesktopSecurityPage(),
    );
  }
}
