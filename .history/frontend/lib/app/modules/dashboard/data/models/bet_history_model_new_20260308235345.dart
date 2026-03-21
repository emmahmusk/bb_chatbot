class BetHistoryModel {
  final int id;
  final String companyName;
  final String logoUrl;
  final String symbol;
  final String outcome;
  final String odds;
  final String strikePrice;
  final String wagerAmount;
  final String expiryDate;
  final String betPlacedDate;
  final String payoutAmount;
  final bool isParlay;
  final String status;

  BetHistoryModel({
    required this.id,
    required this.companyName,
    required this.logoUrl,
    required this.symbol,
    required this.outcome,
    required this.odds,
    required this.strikePrice,
    required this.wagerAmount,
    required this.expiryDate,
    required this.betPlacedDate,
    required this.payoutAmount,
    required this.isParlay,
    required this.status,
  });

  factory BetHistoryModel.fromJson(Map<String, dynamic> json) {
    final marketDetails = json['market_details'];
    final stock = marketDetails != null ? marketDetails['stock'] : null;
    final chosenOutcome = (json['chosen_outcome'] ?? 'N/A').toString().toUpperCase();

    String marketDecimalOdds = 'N/A';
    if (marketDetails != null) {
      final String outcomeLower = chosenOutcome.toLowerCase();
      if (outcomeLower == 'under' && marketDetails['odds_under'] is Map) {
        marketDecimalOdds = marketDetails['odds_under']['decimal']?.toString() ?? 'N/A';
      } else if (marketDetails['odds_over'] is Map) {
        marketDecimalOdds = marketDetails['odds_over']['decimal']?.toString() ?? 'N/A';
      }
    }

    final String placedDecimalOdds =
        _toDecimalOdds(json['odds_at_placement']?.toString()) ?? marketDecimalOdds;

    return BetHistoryModel(
      id: json['id'] ?? 0,
      companyName: stock != null ? stock['company_name'] ?? 'N/A' : 'N/A',
      logoUrl: stock != null ? stock['url'] ?? '' : '',
      symbol: stock != null ? stock['symbol'] ?? 'N/A' : 'N/A',
      outcome: chosenOutcome,
      odds: placedDecimalOdds,
      strikePrice: marketDetails != null
          ? marketDetails['target_price']?.toString() ?? 'N/A'
          : 'N/A',
      wagerAmount: json['amount_wagered']?.toString() ?? 'N/A',
      expiryDate: marketDetails != null && marketDetails['expiry_date'] != null
          ? marketDetails['expiry_date'].toString().split('T').first
          : 'N/A',
      betPlacedDate: json['created_at'] != null
          ? json['created_at'].toString().split('T').first
          : 'N/A',
      payoutAmount: json['payout_amount']?.toString() ?? 'N/A',
      isParlay: json['is_parlay_leg'] ?? false,
      status: json['status'] ?? 'pending',
    );
  }

  static String? _toDecimalOdds(String? oddsAtPlacement) {
    if (oddsAtPlacement == null) return null;
    final raw = oddsAtPlacement.trim();
    if (raw.isEmpty || raw.toUpperCase() == 'N/A') return null;

    final parsed = double.tryParse(raw);
    if (parsed == null) return null;

    double decimal;

    if (parsed < 0 || parsed >= 100) {
      decimal = parsed < 0 ? 1 + (100 / parsed.abs()) : 1 + (parsed / 100);
    } else if (parsed > 1) {
      decimal = parsed;
    } else {
      return null;
    }

    return decimal.toStringAsFixed(2);
  }
}
