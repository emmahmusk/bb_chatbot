import 'package:flutter/widgets.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/desktop_dashboard_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';
import 'package:go_router/go_router.dart';

class DashboardEntry extends StatelessWidget {
  const DashboardEntry({
    super.key,
    required this.shell,
  });
  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => DesktopDashboardPage(shell: shell),
      desktopBuilder: (context) => DesktopDashboardPage(shell: shell),
    );
  }
}
