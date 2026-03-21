import 'package:flutter/material.dart';
import 'package:frontend/app/modules/competition/presentation/responsive/desktop/desktop_competition_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class CompetitionEntry extends StatelessWidget {
  const CompetitionEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (_) => const DesktopCompetitionPage(),
      desktopBuilder: (_) => const DesktopCompetitionPage(),
    );
  }
}
