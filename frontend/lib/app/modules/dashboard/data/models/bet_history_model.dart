class BetHistoryModel {
  final int id;
  final String companyName;
  final String symbol;
  final bool isParlay;
  final String amountWagered;
  final String chosenOutcome;
  final String status; // "pending" or "settled"
  final DateTime createdAt;

  BetHistoryModel({
    required this.id,
    required this.companyName,
    required this.symbol,
    required this.isParlay,
    required this.amountWagered,
    required this.chosenOutcome,
    required this.status,
    required this.createdAt,
  });

  factory BetHistoryModel.fromJson(Map<String, dynamic> json) {
    final marketDetails = json['market_details'] ?? {};
    final stock = marketDetails['stock'] ?? {};
    return BetHistoryModel(
      id: json['id'],
      companyName: stock['company_name'] ?? '',
      symbol: stock['symbol'] ?? '',
      isParlay: json['is_parlay_leg'] ?? false,
      amountWagered: json['amount_wagered'] ?? '0.0',
      chosenOutcome: json['chosen_outcome'] ?? '',
      status: json['status'] ?? 'pending',
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
