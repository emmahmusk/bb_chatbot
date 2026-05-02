import 'package:flutter/material.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/desktop_expiring_soon_page.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/mobile/mobile_markets_page.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class ExpiringSoonEntry extends StatelessWidget {
  const ExpiringSoonEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => const MobileMarketsPage(
        title: 'Expiring Soon',
        subtitle:
            'Last-chance contracts with a cleaner mobile card layout, so nothing important gets squeezed off-screen.',
        path: DashboardRoutes.expiringSoon,
        pagePreferenceKey: 'expiringSoonPage',
        queryParams: {'expiring_soon': 'true'},
      ),
      desktopBuilder: (context) => const DesktopExpiringSoonPage(),
    );
  }
}
