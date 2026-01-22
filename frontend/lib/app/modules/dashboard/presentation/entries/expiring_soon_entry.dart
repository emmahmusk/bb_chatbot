import 'package:flutter/material.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/desktop_expiring_soon_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class ExpiringSoonEntry extends StatelessWidget {
  const ExpiringSoonEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => Container(),
      desktopBuilder: (context) => DesktopExpiringSoonPage(),
    );
  }
}
