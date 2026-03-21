import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/settings/presentation/responsive/widgets/timeline_breakdown.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/classes/media/svgs.dart';
import 'package:frontend/app/shared/functions/date_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/close_icon.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/app/shared/presentation/widgets/row_title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';

class TransactionDetailsDialog extends ConsumerWidget {
  const TransactionDetailsDialog({
    super.key,
    required this.transaction,
  });

  final Map<String, dynamic> transaction;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    final isCredit =
        (transaction['transaction_type'] ?? '').toString().toLowerCase() ==
            'credit';
    final amountUnit = (transaction['amount_unit'] ?? 'BB Cash').toString();
    final displayAmount =
        (transaction['display_amount'] ?? transaction['amount'] ?? '0')
            .toString();
    final description =
        (transaction['description'] ?? 'Wallet transaction').toString();
    final reference = transaction['reference']?.toString();
    final txStatus = _normalizeStatus(transaction['status']?.toString());
    final createdAt = _parseDateTime(transaction['created_at']?.toString());
    final createdAtText = createdAt != null
        ? formatDateTimeToDDMMYYYYHHmm(createdAt)
        : 'N/A';

    final timelineEvents = _buildTimelineEvents(createdAtText, txStatus);
    final iconAsset = isCredit ? Pngs.walletDeposit : Pngs.bankWithdrawal;
    final headerAmount =
        '${isCredit ? '+' : '-'}$displayAmount ${amountUnit == 'BB Cash' ? 'BB Cash' : 'BBC'}';
    final typeLabel = isCredit ? 'Credit' : 'Debit';
    final detailRows = [
      ('Type', typeLabel),
      ('Unit', amountUnit),
      ('Description', description),
      ('Date', createdAtText),
    ];

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
                        iconAsset,
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
                              headerAmount,
                              style: TextStyle(
                                fontSize: 24,
                                color: colors.alwaysWhite,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              typeLabel,
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
                        text: _statusLabel(txStatus),
                        color: _chipBackground(txStatus, colors),
                        textColor: _chipTextColor(txStatus, colors),
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
                  TimelineBreakdown(events: timelineEvents),
                  const SizedBox(height: 56),
                  for (final data in detailRows) ...[
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
                        (reference != null && reference.trim().isNotEmpty)
                            ? reference
                            : 'TX-${transaction['id'] ?? ''}',
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

  static DateTime? _parseDateTime(String? raw) {
    if (raw == null || raw.trim().isEmpty) {
      return null;
    }
    try {
      return DateTime.parse(raw).toLocal();
    } catch (_) {
      return null;
    }
  }

  static String _normalizeStatus(String? raw) {
    final normalized = (raw ?? '').trim().toLowerCase();
    if (normalized == 'pending') {
      return 'pending';
    }
    if (normalized == 'failed') {
      return 'failed';
    }
    return 'successful';
  }

  static String _statusLabel(String status) {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'failed':
        return 'Failed';
      default:
        return 'Complete';
    }
  }

  static List<TimelineEvent> _buildTimelineEvents(
    String createdAtText,
    String status,
  ) {
    if (status == 'pending') {
      return [
        TimelineEvent(
          title: 'Transaction created',
          timestamp: createdAtText,
          isCompleted: true,
        ),
        TimelineEvent(
          title: 'Awaiting confirmation',
          timestamp: createdAtText,
          isCompleted: false,
        ),
      ];
    }

    if (status == 'failed') {
      return [
        TimelineEvent(
          title: 'Transaction created',
          timestamp: createdAtText,
          isCompleted: true,
        ),
        TimelineEvent(
          title: 'Transaction failed',
          timestamp: createdAtText,
          isCompleted: true,
        ),
      ];
    }

    return [
      TimelineEvent(
        title: 'Transaction created',
        timestamp: createdAtText,
        isCompleted: true,
      ),
      TimelineEvent(
        title: 'Transaction completed',
        timestamp: createdAtText,
        isCompleted: true,
      ),
    ];
  }

  static Color _chipBackground(String status, dynamic colors) {
    switch (status) {
      case 'pending':
        return colors.alwaysFFD33D.withValues(alpha: 0.16);
      case 'failed':
        return colors.always8B949E.withValues(alpha: 0.16);
      default:
        return colors.always003D2E;
    }
  }

  static Color _chipTextColor(String status, dynamic colors) {
    switch (status) {
      case 'pending':
        return colors.alwaysFFD33D;
      case 'failed':
        return colors.always8B949E;
      default:
        return colors.always27D07F;
    }
  }
}

class IconChip extends ConsumerWidget {
  const IconChip({
    super.key,
    required this.asset,
    required this.text,
    this.color,
    this.textColor,
    this.borderRadius = 50,
  });
  final String asset;
  final String text;
  final Color? color;
  final Color? textColor;
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
              color: textColor ?? colors.always27D07F,
            ),
          ),
        ],
      ),
    );
  }
}
