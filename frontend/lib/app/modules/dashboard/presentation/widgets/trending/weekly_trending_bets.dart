import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/data/models/markets_model.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/get_bet_list_provider.dart';
import 'package:frontend/app/modules/dashboard/presentation/widgets/trending/bet_item.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class WeeklyTrendingBets extends ConsumerWidget {
  const WeeklyTrendingBets({
    super.key,
    required this.data,
  });

  final (String, List<MarketModel>) data;

  void _handleBetSelection(WidgetRef ref, MarketModel market, String option) {
    final betList = ref.read(betListProvider);
    final existingBetIndex = betList.indexWhere((bet) => bet.id == market.id);

    if (existingBetIndex != -1) {
      // Market already exists in bet list
      final existingBet = betList[existingBetIndex];

      if (existingBet.outcomeType == option) {
        // Same option clicked - remove the bet
        final updatedList = List<MarketModel>.from(betList)
          ..removeAt(existingBetIndex);
        ref.read(betListProvider.notifier).state = updatedList;
      } else {
        // Different option clicked - update the selection
        final updatedMarket = market.copyWith(outcomeType: option);
        final updatedList = List<MarketModel>.from(betList)
          ..[existingBetIndex] = updatedMarket;
        ref.read(betListProvider.notifier).state = updatedList;
      }
    } else {
      // New market - add to bet list
      final newMarket = market.copyWith(outcomeType: option);
      final updatedList = List<MarketModel>.from(betList)..add(newMarket);
      ref.read(betListProvider.notifier).state = updatedList;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final markets = data.$2;
    final nonNullMarkets = markets.where((e) => e.stockCompanyName != null);
    final colors = ref.watch(appThemeProvider).colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          data.$1,
          style: TextStyle(
            fontSize: 24,
            color: colors.alwaysWhite,
            fontWeight: FontWeight.w400,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: 10),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (var item in nonNullMarkets) ...[
                  BetItem(
                    data: item,
                    onOverClick: () => _handleBetSelection(ref, item, 'over'),
                    onUnderClick: () => _handleBetSelection(ref, item, 'under'),
                  ),
                  const SizedBox(height: 24),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }
}
