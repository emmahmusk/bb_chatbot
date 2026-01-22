import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/data/models/markets_model.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/app/shared/presentation/widgets/market_photo.dart';
import 'package:frontend/app/shared/presentation/widgets/row_title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class _Detail {
  final String title;
  final String subtitle;
  _Detail(this.title, this.subtitle);
}

class BetSlipItem extends ConsumerWidget {
  const BetSlipItem({super.key, required this.bet});
  final MarketModel bet;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    final details = <_Detail>[
      _Detail('Strike Price',
          '${bet.outcomeType} • \$${bet.targetPrice.toStringAsFixed(2)}'),
      _Detail('Exp Date', bet.expiryDateFormatted),
      _Detail(
          'Odd',
          bet.outcomeType.toLowerCase() == 'over'
              ? bet.displayOddsOver
              : bet.displayOddsUnder),
    ];
    return Container(
      width: double.maxFinite,
      decoration: BoxDecoration(
        color: colors.always1F242C,
        border: Border.all(
          width: 1,
          color: colors.always30363D,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              MarketPhoto(url: '', stockSymbol: bet.stockSymbol),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    bet.stockCompanyName!,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      letterSpacing: 0,
                      color: colors.alwaysWhite,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    bet.stockSymbol,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      letterSpacing: 0,
                      color: colors.always8B949E,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          for (var i = 0; i < details.length; i++) ...[
            RowTitleSubtitle(
              title: details[i].title,
              subtitle: details[i].subtitle,
            ),
            if (i < details.length - 1) ...[
              const SizedBox(height: 12),
              const CustomDivider(),
              const SizedBox(height: 12),
            ],
          ],
        ],
      ),
    );
  }

  String getOdds() {
    if (bet.outcomeType.toLowerCase() == "over") {
      return bet.displayOddsOver;
    }
    return bet.displayOddsUnder;
  }
}
