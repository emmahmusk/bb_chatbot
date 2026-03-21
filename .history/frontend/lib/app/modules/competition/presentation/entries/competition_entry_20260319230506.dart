import 'package:flutter/material.dart';
import 'package:frontend/app/modules/competition/presentation/responsive/mobile/mobile_competition_page.dart';
import 'package:frontend/app/modules/competition/presentation/responsive/desktop/desktop_competition_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class CompetitionEntry extends StatelessWidget {
  const CompetitionEntry({
    super.key,
    this.selectedCompetitionId,
    this.initialQuery = '',
    this.initialStatus = 'registration',
    this.initialOrdering = 'start_date',
    this.initialTab = 'discover',
  });

  final int? selectedCompetitionId;
  final String initialQuery;
  final String initialStatus;
  final String initialOrdering;
  final String initialTab;

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (_) => MobileCompetitionPage(
        selectedCompetitionId: selectedCompetitionId,
        initialQuery: initialQuery,
        initialStatus: initialStatus,
        initialOrdering: initialOrdering,
        initialTab: initialTab,
      ),
      desktopBuilder: (_) => DesktopCompetitionPage(
        selectedCompetitionId: selectedCompetitionId,
        initialQuery: initialQuery,
        initialStatus: initialStatus,
        initialOrdering: initialOrdering,
        initialTab: initialTab,
      ),
    );
  }
}
