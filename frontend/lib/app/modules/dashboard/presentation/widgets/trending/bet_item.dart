import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/data/models/markets_model.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/get_bet_list_provider.dart';
import 'package:frontend/app/modules/dashboard/presentation/widgets/trending/bet_option.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/market_photo.dart';
import 'package:frontend/app/shared/presentation/widgets/row_title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class BetItem extends ConsumerStatefulWidget {
  const BetItem({
    super.key,
    required this.data,
    required this.onOverClick,
    required this.onUnderClick,
  });
  final MarketModel data;
  final VoidCallback onOverClick;
  final VoidCallback onUnderClick;

  @override
  ConsumerState<BetItem> createState() => _BetItemState();
}

class _BetItemState extends ConsumerState<BetItem> {
  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final betList = ref.watch(betListProvider);

    // Check if this market is selected (either over or under)
    final isOverSelected = betList.any((bet) =>
        bet.id == widget.data.id && bet.outcomeType.toLowerCase() == 'over');
    final isUnderSelected = betList.any((bet) =>
        bet.id == widget.data.id && bet.outcomeType.toLowerCase() == 'under');
    return Clickable(
      onClick: () {
        ref.read(betListProvider.notifier).state.add(widget.data);
      },
      child: Container(
        height: 170,
        width: double.maxFinite,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.always30363D),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 3,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              MarketPhoto(
                                  url: '',
                                  stockSymbol: widget.data.stockSymbol),
                              const SizedBox(width: 10),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(
                                        widget.data.stockCompanyName!,
                                        style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w500,
                                          letterSpacing: 0,
                                          color: colors.alwaysWhite,
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Container(
                                        width: 5,
                                        height: 5,
                                        decoration: BoxDecoration(
                                          shape: BoxShape.circle,
                                          color: colors.always8B949E,
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Text(
                                        widget.data.stockSymbol,
                                        style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w500,
                                          letterSpacing: 0,
                                          color: colors.always8B949E,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 4),
                                  Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(
                                        "\$" "${widget.data.targetPrice}",
                                        style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w500,
                                          letterSpacing: 0,
                                          color: colors.alwaysWhite,
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      // Image.asset(
                                      //   priceChangeValues(trendingBets, data, colors)
                                      //       .$2,
                                      //   fit: BoxFit.cover,
                                      //   height: 16,
                                      //   width: 16,
                                      // ),
                                      // const SizedBox(width: 4),
                                      // Text(
                                      //   data.priceChangeAndPricePercentChange,
                                      //   style: TextStyle(
                                      //     fontSize: 14,
                                      //     color: priceChangeValues(
                                      //             trendingBets, data, colors)
                                      //         .$1,
                                      //     fontWeight: FontWeight.w400,
                                      //   ),
                                      // ),
                                    ],
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Container(
                            width: 250,
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 8),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(12),
                              color: colors.always1F242C,
                            ),
                            child: RowTitleSubtitle(
                              title: 'Strike price',
                              subtitle:
                                  "\$${widget.data.targetPrice.toStringAsFixed(2)}",
                            ),
                          ),
                        ],
                      ),
                    ),
                    Row(
                      children: [
                        BetOption(
                          title: 'Over',
                          value: double.parse(widget.data.displayOddsOver),
                          isSelected: isOverSelected,
                          onClick: widget.onOverClick,
                        ),
                        const SizedBox(width: 16),
                        BetOption(
                          title: 'Under',
                          value: double.parse(widget.data.displayOddsUnder),
                          isSelected: isUnderSelected,
                          onClick: widget.onUnderClick,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            Expanded(
              flex: 1,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                decoration: BoxDecoration(
                  color: colors.always1F242C,
                  borderRadius: BorderRadius.only(
                    bottomLeft: Radius.circular(16),
                    bottomRight: Radius.circular(16),
                  ),
                ),
                child: Row(
                  children: [
                    Text(
                      'Exp: ',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w400,
                        color: colors.alwaysWhite.withValues(alpha: 0.4),
                      ),
                    ),
                    Text(
                      widget.data.expiryDateFormatted,
                      style: TextStyle(
                        fontSize: 14,
                        color: colors.alwaysWhite,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
