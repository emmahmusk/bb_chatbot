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

class _DesktopAllBetsPageState extends ConsumerState<DesktopAllBetsPage> {
  String selectedTab = 'Live';
  final ScrollController _scrollController = ScrollController();

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
                  final filtered = bets
                      .where((b) => selectedTab == 'Live'
                          ? b.status == 'pending'
                          : b.status != 'pending')
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
    final double parsedOdds = double.tryParse(item.odds) ?? 0.0;
    final int odds = parsedOdds.round();

    final double potentialPayout = odds < 0
        ? (amount / odds.abs()) * 100 + amount
        : (amount * (odds / 100)) + amount;

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
          _infoRow("Status", _statusText(item.status)),

          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 10.0),
            child: Divider(color: Colors.grey, thickness: 1),
          ),
          _infoRow(
              "Potential Payout", "${potentialPayout.toStringAsFixed(2)} BBC"),
        ],
      ),
    );
  }

  String _statusText(String status) {
    switch (status) {
      case 'won':
        return 'WON';
      case 'lost':
        return 'LOST';
      default:
        return 'LIVE';
    }
  }

  Widget _infoRow(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.white)),
          Text(value, style: const TextStyle(color: Colors.white)),
        ],
      ),
    );
  }
}
