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
    this.initialDiscoverPage = 1,
    this.initialMyPage = 1,
    this.initialMyStatus = 'live',
    this.initialLeaderboardPage = 1,
    this.initialPageSize = 20,
  });

  final int? selectedCompetitionId;
  final String initialQuery;
  final String initialStatus;
  final String initialOrdering;
  final String initialTab;
  final int initialDiscoverPage;
  final int initialMyPage;
  final String initialMyStatus;
  final int initialLeaderboardPage;
  final int initialPageSize;

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
        initialDiscoverPage: initialDiscoverPage,
        initialMyPage: initialMyPage,
        initialMyStatus: initialMyStatus,
        initialLeaderboardPage: initialLeaderboardPage,
        initialPageSize: initialPageSize,
      ),
      desktopBuilder: (_) => DesktopCompetitionPage(
        selectedCompetitionId: selectedCompetitionId,
        initialQuery: initialQuery,
        initialStatus: initialStatus,
        initialOrdering: initialOrdering,
        initialTab: initialTab,
        initialDiscoverPage: initialDiscoverPage,
        initialMyPage: initialMyPage,
        initialMyStatus: initialMyStatus,
        initialLeaderboardPage: initialLeaderboardPage,
        initialPageSize: initialPageSize,
      ),
    );
  }
}
