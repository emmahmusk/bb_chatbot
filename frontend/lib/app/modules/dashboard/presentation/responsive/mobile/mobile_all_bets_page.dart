import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/data/models/bet_history_model_new.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/bet_history_provider_new.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/loading_main_card.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class MobileAllBetsPage extends ConsumerStatefulWidget {
  const MobileAllBetsPage({super.key});

  @override
  ConsumerState<MobileAllBetsPage> createState() => _MobileAllBetsPageState();
}

class _MobileAllBetsPageState extends ConsumerState<MobileAllBetsPage> {
  String _selectedTab = 'Live';
  bool _didFetchForThisActivation = false;

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final betsAsync = ref.watch(betHistoryProvider);

    if (!_didFetchForThisActivation && isAuthenticated()) {
      WidgetsBinding.instance.addPostFrameCallback((_) async {
        if (!mounted) return;
        _didFetchForThisActivation = true;
        await ref.read(betHistoryProvider.notifier).get();
      });
    }

    if (!isAuthenticated()) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: colors.always30363D),
          color: const Color(0xFF11151D),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.lock_outline_rounded,
              color: colors.alwaysWhite.withValues(alpha: 0.72),
              size: 28,
            ),
            const SizedBox(height: 12),
            Text(
              'Sign in to view your predictions.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: colors.alwaysWhite,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: colors.always30363D),
        color: const Color(0xFF11151D),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'My Predictions',
            style: TextStyle(
              color: colors.alwaysWhite,
              fontSize: 28,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Track the slips that are still live and the ones already settled.',
            style: TextStyle(
              color: colors.alwaysWhite.withValues(alpha: 0.68),
              fontSize: 14,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _HistoryTab(
                  label: 'Live',
                  selected: _selectedTab == 'Live',
                  onTap: () => setState(() => _selectedTab = 'Live'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _HistoryTab(
                  label: 'Settled',
                  selected: _selectedTab == 'Settled',
                  onTap: () => setState(() => _selectedTab = 'Settled'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: betsAsync.when(
              loading: () => const Center(child: LoadingMainCard()),
              error: (error, _) => Center(
                child: Text(
                  'We could not load your prediction history.\n$error',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white70, height: 1.4),
                ),
              ),
              data: (bets) {
                final filtered = _filterBets(bets);
                if (filtered.isEmpty) {
                  return Center(
                    child: Text(
                      _selectedTab == 'Live'
                          ? 'No live predictions yet.'
                          : 'No settled predictions yet.',
                      style: TextStyle(
                        color: colors.alwaysWhite.withValues(alpha: 0.72),
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  );
                }

                return ListView.separated(
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 14),
                  itemBuilder: (context, index) => _HistoryCard(
                    bet: filtered[index],
                    isSettled: _selectedTab == 'Settled',
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  List<BetHistoryModel> _filterBets(List<BetHistoryModel> bets) {
    final today = DateUtils.dateOnly(DateTime.now());
    return bets.where((bet) {
      final isPending = bet.status.toLowerCase() == 'pending';
      final expiry = DateTime.tryParse(bet.expiryDate);
      final expiryDate = expiry == null ? today : DateUtils.dateOnly(expiry);
      final isExpired = expiryDate.isBefore(today);

      if (_selectedTab == 'Live') {
        return isPending && !isExpired;
      }

      return !isPending || isExpired;
    }).toList();
  }
}

class _HistoryTab extends ConsumerWidget {
  const _HistoryTab({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: selected ? colors.alwaysWhite : colors.always30363D.withValues(alpha: 0.24),
          border: Border.all(
            color: selected ? colors.alwaysWhite : colors.always30363D,
          ),
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              color: selected ? colors.primary : colors.alwaysWhite,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }
}

class _HistoryCard extends ConsumerWidget {
  const _HistoryCard({
    required this.bet,
    required this.isSettled,
  });

  final BetHistoryModel bet;
  final bool isSettled;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    final wagerAmount = double.tryParse(bet.wagerAmount) ?? 0.0;
    final payoutAmount = double.tryParse(bet.payoutAmount) ?? 0.0;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colors.always30363D),
        color: colors.always30363D.withValues(alpha: 0.18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _HistoryLogo(symbol: bet.symbol, logoUrl: bet.logoUrl),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      bet.companyName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: colors.alwaysWhite,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '\$${bet.symbol} - ${bet.outcome}',
                      style: TextStyle(
                        color: colors.alwaysWhite.withValues(alpha: 0.6),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  color: isSettled ? colors.alwaysWhite : Colors.greenAccent.withValues(alpha: 0.14),
                ),
                child: Text(
                  isSettled ? bet.status.toUpperCase() : 'LIVE',
                  style: TextStyle(
                    color: isSettled ? colors.primary : Colors.greenAccent,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _HistoryPill(
                iconAsset: Pngs.strikePrice,
                label: 'Strike ${bet.strikePrice}',
              ),
              _HistoryPill(
                icon: Icons.calendar_today_outlined,
                label: bet.expiryDate,
              ),
              _HistoryPill(
                icon: Icons.stacked_line_chart_rounded,
                label: 'Odds ${bet.odds}',
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _HistoryAmount(
                  label: 'Stake',
                  value: wagerAmount.toStringAsFixed(2),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _HistoryAmount(
                  label: isSettled ? 'Payout' : 'Potential',
                  value: (isSettled ? payoutAmount : _estimatePayout(wagerAmount, bet.odds))
                      .toStringAsFixed(2),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  double _estimatePayout(double wagerAmount, String oddsText) {
    final odds = double.tryParse(oddsText) ?? 1.0;
    return wagerAmount * math.max(odds, 1.0);
  }
}

class _HistoryLogo extends StatelessWidget {
  const _HistoryLogo({
    required this.symbol,
    required this.logoUrl,
  });

  final String symbol;
  final String logoUrl;

  @override
  Widget build(BuildContext context) {
    if (logoUrl.isNotEmpty) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Image.network(
          logoUrl,
          width: 44,
          height: 44,
          fit: BoxFit.cover,
        ),
      );
    }

    return Container(
      width: 44,
      height: 44,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: Colors.white,
      ),
      child: Text(
        symbol.substring(0, symbol.length >= 2 ? 2 : 1).toUpperCase(),
        style: const TextStyle(
          color: Colors.black,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _HistoryPill extends ConsumerWidget {
  const _HistoryPill({
    required this.label,
    this.icon,
    this.iconAsset,
  });

  final String label;
  final IconData? icon;
  final String? iconAsset;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: colors.always30363D.withValues(alpha: 0.32),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null)
            Icon(icon, size: 14, color: colors.alwaysWhite.withValues(alpha: 0.72)),
          if (iconAsset != null)
            Image.asset(
              iconAsset!,
              width: 14,
              height: 14,
              fit: BoxFit.contain,
            ),
          const SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(
              color: colors.alwaysWhite,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _HistoryAmount extends ConsumerWidget {
  const _HistoryAmount({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: colors.always30363D),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: colors.alwaysWhite.withValues(alpha: 0.6),
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            '$value BBC',
            style: TextStyle(
              color: colors.alwaysWhite,
              fontSize: 15,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
