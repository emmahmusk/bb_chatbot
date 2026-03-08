import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:math';
import '../../providers/bet_history_provider_new.dart';
import '../../../data/models/bet_history_model_new.dart';
import 'package:frontend/app/shared/presentation/widgets/loading_main_card.dart';

class DesktopAllBetsPage extends ConsumerStatefulWidget {
  const DesktopAllBetsPage({super.key});

  @override
  ConsumerState<DesktopAllBetsPage> createState() => _DesktopAllBetsPageState();
}

class _DesktopAllBetsPageState extends ConsumerState<DesktopAllBetsPage>
  with SingleTickerProviderStateMixin {
  String selectedTab = 'Live';
  final ScrollController _scrollController = ScrollController();
  late final AnimationController _blinkController;

  @override
  void initState() {
    super.initState();
    _blinkController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 850),
      lowerBound: 0.25,
      upperBound: 1.0,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _blinkController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final betAsyncValue = ref.watch(betHistoryProvider);

    return Padding(
      padding: const EdgeInsets.only(left: 40),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: const Color(0xFF1F242C)),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "My Predictions",
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                _buildChip('Live'),
                const SizedBox(width: 10),
                _buildChip('Settled'),
              ],
            ),
            const SizedBox(height: 16),
            Expanded(
              child: betAsyncValue.when(
                loading: () => const Center(child: LoadingMainCard()),
                error: (e, _) => Center(
                  child: Text("Error: $e",
                      style: const TextStyle(color: Colors.white)),
                ),
                data: (bets) {
                  final today = DateUtils.dateOnly(DateTime.now());

                  final filtered = bets
                      .where((b) {
                        final isPending = b.status.toLowerCase() == 'pending';
                        final isExpired = _isExpired(b, today);

                        if (selectedTab == 'Live') {
                          return isPending && !isExpired;
                        }

                        return !isPending || isExpired;
                      })
                      .toList();

                  return Scrollbar(
                    controller: _scrollController,
                    thumbVisibility: true,
                    thickness: 6,
                    radius: const Radius.circular(10),
                    interactive: true,
                    child: SingleChildScrollView(
                      controller: _scrollController,
                      child: Wrap(
                        direction: Axis.horizontal,
                        spacing: 16,
                        runSpacing: 16,
                        children: filtered
                            .map((bet) => SizedBox(
                                  width: 300,
                                  child: buildBetItem(bet),
                                ))
                            .toList(),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChip(String label) {
    final isSelected = selectedTab == label;
    return GestureDetector(
      onTap: () => setState(() => selectedTab = label),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? Colors.white : Colors.black,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isSelected ? Colors.black : Colors.white),
        ),
        child: Text(
          label,
          style: TextStyle(color: isSelected ? Colors.black : Colors.white),
        ),
      ),
    );
  }

  Widget buildBetItem(BetHistoryModel item) {
    final double amount = double.tryParse(item.wagerAmount) ?? 0.0;
    final bool isSettled = item.status != 'pending';
    final double settledPayout = double.tryParse(item.payoutAmount) ?? 0.0;
    final double potentialPayout = _calculatePotentialPayout(
      wagerAmount: amount,
      oddsText: item.odds,
    );

    return Container(
      margin: const EdgeInsets.all(8.0),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade800),
        borderRadius: BorderRadius.circular(12),
        color: const Color(0xFF1F242C),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            decoration: BoxDecoration(
              color: Colors.black,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              child: Row(
                children: [
                  (item.logoUrl != null)
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: Image.network(
                            item.logoUrl,
                            width: 32,
                            height: 32,
                            fit: BoxFit.cover,
                          ),
                        )
                      : Container(
                          width: 32,
                          height: 32,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            item.symbol.substring(0, min(2, item.symbol.length)),
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.black,
                            ),
                          ),
                        ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (item.companyName != null)
                        SizedBox(
                          width:
                              min(MediaQuery.of(context).size.width * 0.5, 200),
                          child: Text(
                            item.companyName!,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      const SizedBox(height: 4),
                      Text(
                        "\$${item.symbol}",
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  )
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          _infoRow("Date Placed", item.betPlacedDate),
          _infoRow("Odd", "${item.outcome} - ${item.odds}"),
          _infoRow("Strike Price", "\$${item.strikePrice}"),
          _infoRow("Exp date", item.expiryDate),
          _infoRow("Wager Amount", "${item.wagerAmount} BBC"),
          _infoRow("Single/Parlay", item.isParlay ? "Parlay" : "Single"),

          /// ✅ NEW ROW (ONLY ADDITION)
          _statusRow(item),

          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 10.0),
            child: Divider(color: Colors.grey, thickness: 1),
          ),
          _infoRow(
            isSettled ? "Payout" : "Potential Payout",
            "${(isSettled ? settledPayout : potentialPayout).toStringAsFixed(2)} BBC",
          ),
        ],
      ),
    );
  }

  double _calculatePotentialPayout({
    required double wagerAmount,
    required String oddsText,
  }) {
    final trimmed = oddsText.trim();
    if (wagerAmount <= 0 || trimmed.isEmpty || trimmed == 'N/A') return 0.0;

    final parsedOdds = double.tryParse(trimmed);
    if (parsedOdds == null) return 0.0;

    if (parsedOdds < 0 || parsedOdds >= 100) {
      return parsedOdds < 0
          ? (wagerAmount / parsedOdds.abs()) * 100 + wagerAmount
          : (wagerAmount * (parsedOdds / 100)) + wagerAmount;
    }

    if (parsedOdds > 1) {
      return wagerAmount * parsedOdds;
    }

    return 0.0;
  }

  String _statusText(String status) {
    switch (status) {
      case 'won':
        return 'WON';
      case 'lost':
        return 'LOST';
      case 'void':
        return 'VOID';
      default:
        return 'LIVE';
    }
  }

  bool _isExpired(BetHistoryModel item, DateTime today) {
    try {
      final expiry = DateUtils.dateOnly(DateTime.parse(item.expiryDate));
      return expiry.isBefore(today);
    } catch (_) {
      return false;
    }
  }

  Widget _statusRow(BetHistoryModel item) {
    final normalized = item.status.toLowerCase();

    if (normalized == 'won') {
      return _infoRow(
        "Status",
        "WON",
        valueStyle: const TextStyle(
          color: Color(0xFF22C55E),
          fontWeight: FontWeight.w700,
        ),
      );
    }

    if (normalized == 'lost') {
      return _infoRow(
        "Status",
        "LOST",
        valueStyle: const TextStyle(
          color: Color(0xFFEF4444),
          fontWeight: FontWeight.w700,
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text("Status", style: TextStyle(color: Colors.white)),
          Row(
            children: [
              FadeTransition(
                opacity: _blinkController,
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: Color(0xFF22C55E),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              const Text(
                "LIVE",
                style: TextStyle(
                  color: Color(0xFF22C55E),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value, {TextStyle? valueStyle}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.white)),
          Text(value, style: valueStyle ?? const TextStyle(color: Colors.white)),
        ],
      ),
    );
  }
}
