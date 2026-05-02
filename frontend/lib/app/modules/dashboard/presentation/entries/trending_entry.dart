import 'package:flutter/material.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/desktop_trending_page.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/mobile/mobile_markets_page.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class TrendingEntry extends StatelessWidget {
  const TrendingEntry({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => const MobileMarketsPage(
        title: 'Trending Predictions',
        subtitle: 'Fast-moving stock contracts with strong market momentum.',
        path: DashboardRoutes.trending,
        pagePreferenceKey: 'trendingPage',
        queryParams: {'trending': 'true'},
      ),
      desktopBuilder: (context) => const DesktopTrendingPage(initialPage: '1'),
    );
  }
}
