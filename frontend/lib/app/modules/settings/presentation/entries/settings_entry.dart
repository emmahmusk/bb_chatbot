import 'package:flutter/widgets.dart';
import 'package:frontend/app/modules/settings/presentation/responsive/mobile/mobile_settings_page.dart';
import 'package:frontend/app/modules/settings/presentation/responsive/desktop/desktop_settings_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';
import 'package:go_router/go_router.dart';

class SettingsEntry extends StatelessWidget {
  const SettingsEntry({super.key, required this.shell});
  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => MobileSettingsPage(shell: shell),
      desktopBuilder: (context) => DesktopSettingsPage(shell: shell),
    );
  }
}
