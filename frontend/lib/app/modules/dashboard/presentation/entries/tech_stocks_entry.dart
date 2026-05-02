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
            'A full market view of available stock contracts across active listings.',
        path: DashboardRoutes.allStocks,
        pagePreferenceKey: 'allStocksPage',
      ),
      desktopBuilder: (context) => const DesktopTechStocksPage(),
    );
  }
}
