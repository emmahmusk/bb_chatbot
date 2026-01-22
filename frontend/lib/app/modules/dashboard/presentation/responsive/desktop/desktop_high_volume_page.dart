import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/get_markets_provider.dart';
import 'package:frontend/app/modules/dashboard/presentation/widgets/trending/weekly_trending_bets.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/loadable_section.dart';

class DesktopHighVolumePage extends ConsumerStatefulWidget {
  const DesktopHighVolumePage({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _DesktopHighVolumePageState();
}

class _DesktopHighVolumePageState extends ConsumerState<DesktopHighVolumePage> {
  @override
  void initState() {
    onInit(
      () {
        ref.read(getMarketsProvider.notifier).get();
      },
    );
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 40),
      child: LoadableSection(
        state: ref.watch(getMarketsProvider),
        builder: (context, markets) {
          final highVolume = markets.where((e) => e.targetPrice > 200).toList();
          return WeeklyTrendingBets(
            data: ('High Volume', highVolume),
          );
        },
      ),
    );
  }
}
