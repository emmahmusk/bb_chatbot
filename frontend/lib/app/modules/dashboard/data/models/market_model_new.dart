class Stock {
  final String symbol;
  final String? companyName;
  final String? logoUrl;
  final DateTime updatedAt;
  final DateTime createdAt;

  Stock({
    required this.symbol,
    this.companyName,
    this.logoUrl,
    required this.updatedAt,
    required this.createdAt,
  });

  factory Stock.fromJson(Map<String, dynamic> json) {
    return Stock(
      symbol: json['symbol'].toString(),
      companyName: json['company_name']?.toString(),
      logoUrl: json['url']?.toString(),
      updatedAt: DateTime.parse(json['updated_at'].toString()),
      createdAt: DateTime.parse(json['created_at'].toString()),
    );
  }
}

class MarketModel {
  final int id;
  final Stock stock;
  final double targetPrice;
  final String expiryDate;
  final String outcomeType;
  final String impliedOddsOver;
  final String impliedOddsUnder;
  final bool isActive;

  // Explicitly extracted odds
  final String? oddsAOver;
  final String? oddsAUnder;
  final String? oddsDOver;
  final String? oddsDUnder;
  final String? oddsFOver;
  final String? oddsFUnder;

  MarketModel({
    required this.id,
    required this.stock,
    required this.targetPrice,
    required this.expiryDate,
    required this.outcomeType,
    required this.impliedOddsOver,
    required this.impliedOddsUnder,
    required this.isActive,
    this.oddsAOver,
    this.oddsAUnder,
    this.oddsDOver,
    this.oddsDUnder,
    this.oddsFOver,
    this.oddsFUnder,
  });


   /// ✅ Add this static method at the end of your class
  static MarketModel empty() {
    return MarketModel(
      id: -1,
      stock: Stock(
        symbol: '',
        companyName: null,
        logoUrl: null,
        updatedAt: DateTime.now(),
        createdAt: DateTime.now(),
      ),
      targetPrice: 0.0,
      expiryDate: '',
      outcomeType: '',
      impliedOddsOver: '',
      impliedOddsUnder: '',
      isActive: false,
      oddsAOver: null,
      oddsAUnder: null,
      oddsDOver: null,
      oddsDUnder: null,
      oddsFOver: null,
      oddsFUnder: null,
    );
  }

  factory MarketModel.fromJson(Map<String, dynamic> json) {
    final oddsOver = json['odds_over'] ?? {};
    final oddsUnder = json['odds_under'] ?? {};

    return MarketModel(
      id: json['id'],
      stock: Stock.fromJson(json['stock']),
      targetPrice: double.tryParse(json['target_price'].toString()) ?? 0.0,
      expiryDate: json['expiry_date'].toString(),
      outcomeType: json['outcome_type'].toString(),
      impliedOddsOver: json['implied_odds_over'].toString(),
      impliedOddsUnder: json['implied_odds_under'].toString(),
      isActive: json['is_active'] ?? false,

      oddsAOver: oddsOver['american']?.toString(),
      oddsAUnder: oddsUnder['american']?.toString(),
      oddsDOver: oddsOver['decimal']?.toString(),
      oddsDUnder: oddsUnder['decimal']?.toString(),
      oddsFOver: oddsOver['fractional']?.toString(),
      oddsFUnder: oddsUnder['fractional']?.toString(),
    );
  }
}

class PaginatedMarketModel {
  final List<MarketModel> results;
  final int totalCount;
  final int totalPages;

  PaginatedMarketModel({
    required this.results,
    required this.totalCount,
    required this.totalPages,
  });

  factory PaginatedMarketModel.fromJson(Map<String, dynamic> json) {
    final int count = json['count'] ?? 0;
    final int pageSize = 10;
    final int totalPages = (count / pageSize).ceil();

    return PaginatedMarketModel(
      results: (json['results'] as List)
          .map((e) => MarketModel.fromJson(e))
          .toList(),
      totalCount: count,
      totalPages: totalPages,
    );
  }

  /// ✅ Manually added copyWith method
  PaginatedMarketModel copyWith({
    List<MarketModel>? results,
    int? totalCount,
    int? totalPages,
  }) {
    return PaginatedMarketModel(
      results: results ?? this.results,
      totalCount: totalCount ?? this.totalCount,
      totalPages: totalPages ?? this.totalPages,
    );
  }
}
