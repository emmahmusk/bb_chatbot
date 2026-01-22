class MarketDetails {
  final int id;
  final String stockSymbol;
  final String? stockCompanyName;
  final String targetPrice;
  final String expiryDate;
  final String outcomeType;
  final String displayOddsOver;
  final String displayOddsUnder;
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;

  MarketDetails({
    required this.id,
    required this.stockSymbol,
    required this.stockCompanyName,
    required this.targetPrice,
    required this.expiryDate,
    required this.outcomeType,
    required this.displayOddsOver,
    required this.displayOddsUnder,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
  });

  factory MarketDetails.fromJson(Map<String, dynamic> json) {
    return MarketDetails(
      id: json['id'],
      stockSymbol: json['stock_symbol'],
      stockCompanyName: json['stock_company_name'],
      targetPrice: json['target_price'],
      expiryDate: json['expiry_date'],
      outcomeType: json['outcome_type'],
      displayOddsOver: json['display_odds_over'],
      displayOddsUnder: json['display_odds_under'],
      isActive: json['is_active'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}
