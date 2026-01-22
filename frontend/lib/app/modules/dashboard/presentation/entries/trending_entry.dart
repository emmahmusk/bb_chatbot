import 'package:flutter/material.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/desktop_trending_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class TrendingEntry extends StatelessWidget {
  const TrendingEntry({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => Container(),
      desktopBuilder: (context) => const DesktopTrendingPage(initialPage: '1'),
    );
  }
}
