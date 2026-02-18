import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/settings/presentation/responsive/widgets/timeline_breakdown.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/classes/media/svgs.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/close_icon.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/app/shared/presentation/widgets/row_title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';

class TransactionDetailsDialog extends ConsumerStatefulWidget {
  const TransactionDetailsDialog({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _TransactionDetailsDialogState();
}

class _TransactionDetailsDialogState
    extends ConsumerState<TransactionDetailsDialog> {
  List<TimelineEvent> get _timelineEvents => [
        const TimelineEvent(
          title: 'Withdrawal requested',
          timestamp: '04/02/2025, 13:17',
          isCompleted: true,
        ),
        const TimelineEvent(
          title: 'Money sent',
          timestamp: '04/02/2025, 13:17',
          isCompleted: true,
        ),
      ];

  final transactionDetails = [
    (
      'Account name',
      'Darrell Steward',
    ),
    (
      'Account number',
      '87290395',
    ),
    (
      'Sort code',
      '295830',
    ),
  ];
  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    return Container(
      width: 686,
      height: 700,
      decoration: BoxDecoration(
        color: colors.always161B22,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: colors.always30363D.withValues(alpha: 0.3),
        ),
      ),
      padding: const EdgeInsets.all(24),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Container(),
                const Spacer(),
                Column(
                  children: [
                    Text(
                      'Transaction details',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w600,
                        color: colors.alwaysWhite,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Details about this transaction.',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w400,
                        color: colors.always8B949E,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                CloseIcon(
                  svg: Svgs.close,
                  onTap: () => pop(context),
                ),
              ],
            ),
            const SizedBox(height: 44),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Image.asset(
                        Pngs.bankWithdrawal,
                        width: 40,
                        height: 40,
                        fit: BoxFit.cover,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '-£4.50',
                              style: TextStyle(
                                fontSize: 24,
                                color: colors.alwaysWhite,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Withdrawal',
                              style: TextStyle(
                                fontSize: 14,
                                color: colors.alwaysWhite,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      IconChip(
                        asset: Pngs.checkCircle,
                        text: "Complete",
                      ),
                    ],
                  ),
                  const SizedBox(height: 44),
                  Text(
                    'Timeline Breakdown',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w400,
                      color: colors.alwaysWhite,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            CustomDivider(),
            const SizedBox(height: 16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TimelineBreakdown(events: _timelineEvents),
                  const SizedBox(height: 56),
                  for (var data in transactionDetails) ...[
                    RowTitleSubtitle(
                      title: data.$1,
                      subtitle: data.$2,
                      titleColor: colors.always8B949E,
                      titleSize: 14,
                      subtitleSize: 14,
                    ),
                    const SizedBox(height: 24),
                  ],
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Expanded(
                        child: Text(
                          'ID',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: colors.always8B949E,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        'WL-56ZNLXQUYR',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: colors.alwaysWhite,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Clickable(
                        onClick: () {
                          //TODO: Implement copy
                        },
                        child: Image.asset(
                          Pngs.copy,
                          width: 12,
                          height: 12,
                          fit: BoxFit.cover,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class IconChip extends ConsumerWidget {
  const IconChip({
    super.key,
    required this.asset,
    required this.text,
    this.color,
    this.borderRadius = 50,
  });
  final String asset;
  final String text;
  final Color? color;
  final double borderRadius;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(borderRadius),
        color: color ?? colors.always003D2E,
      ),
      child: Row(
        children: [
          Image.asset(
            asset,
            width: 16,
            height: 16,
            fit: BoxFit.cover,
          ),
          const SizedBox(width: 8),
          Text(
            text,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w400,
              color: colors.always27D07F,
            ),
          ),
        ],
      ),
    );
  }
}
