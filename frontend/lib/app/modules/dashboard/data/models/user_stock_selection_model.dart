class SelectedStockModel {
  final int marketId;
  final String marketName;
  final String chosenOutcome; // 'over' or 'under'
  final String? odds; // Display odds (may be formatted as A/D/F/P based on preference)
  final String? decimalOdds; // Always decimal odds for calculation

  final String companyName;
  final String companySymbol;
  final String logoUrl;
  final double? targetPrice;
  final String expiryDate;
  final double? exposureOver;
  final double? exposureUnder;
  final bool requiresAdminOverride;

  SelectedStockModel({
    required this.marketId,
    required this.marketName,
    required this.chosenOutcome,
    required this.odds,
    required this.companyName,
    required this.companySymbol,
    required this.logoUrl,
    required this.targetPrice,
    required this.expiryDate,
    this.decimalOdds,
    this.exposureOver,
    this.exposureUnder,
    this.requiresAdminOverride = false,
  });

  Map<String, dynamic> toJson() {
    return {
      'market_id': marketId,
      'market_name': marketName,
      'chosen_outcome': chosenOutcome,
      'odds': odds,
      'decimal_odds': decimalOdds,
      'exposure_over': exposureOver,
      'exposure_under': exposureUnder,
      'requires_admin_override': requiresAdminOverride,
      'company_name': companyName,
      'company_symbol': companySymbol,
      'logo_url': logoUrl,
      'target_price': targetPrice,
      'expiry_date': expiryDate,
    };
  }

  factory SelectedStockModel.fromJson(Map<String, dynamic> json) {
    return SelectedStockModel(
      marketId: json['market_id'],
      marketName: json['market_name'],
      chosenOutcome: json['chosen_outcome'],
      odds: (json['odds'] as num?)?.toString(),
      companyName: json['company_name'],
      companySymbol: json['company_symbol'],
      logoUrl: json['logo_url'],
      targetPrice: (json['target_price'] as num?)?.toDouble(),
      expiryDate: json['expiry_date'],
      decimalOdds: json['decimal_odds']?.toString(),
      exposureOver: json['exposure_over'] != null
          ? double.tryParse(json['exposure_over'].toString())
          : null,
      exposureUnder: json['exposure_under'] != null
          ? double.tryParse(json['exposure_under'].toString())
          : null,
      requiresAdminOverride: json['requires_admin_override'] == true,
    );
  }
}
