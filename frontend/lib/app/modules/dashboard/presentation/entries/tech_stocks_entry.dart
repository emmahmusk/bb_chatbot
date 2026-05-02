import 'package:flutter/material.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/desktop_tech_stocks_page.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/mobile/mobile_markets_page.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class TechStocksEntry extends StatelessWidget {
  const TechStocksEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => const MobileMarketsPage(
        title: 'All Stocks',
        subtitle:
            'Browse the full market board in stacked mobile cards with clearer expiry, strike, and direction controls.',
        path: DashboardRoutes.allStocks,
        pagePreferenceKey: 'allStocksPage',
      ),
      desktopBuilder: (context) => const DesktopTechStocksPage(),
    );
  }
}
