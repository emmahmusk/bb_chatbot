import 'package:flutter/material.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/desktop_all_bets_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class AllBetsEntry extends StatelessWidget {
  const AllBetsEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => Container(),
      desktopBuilder: (context) => DesktopAllBetsPage(),
    );
  }
}
