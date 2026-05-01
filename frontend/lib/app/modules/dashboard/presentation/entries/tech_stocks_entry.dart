import 'package:flutter/material.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/desktop_tech_stocks_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class TechStocksEntry extends StatelessWidget {
  const TechStocksEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => DesktopTechStocksPage(),
      desktopBuilder: (context) => DesktopTechStocksPage(),
    );
  }
}
