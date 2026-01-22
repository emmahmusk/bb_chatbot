import 'package:frontend/app/shared/functions/date_functions.dart';

class TrendingBetModel {
  /// e.g. “Tesla, Inc.”
  final String companyName;

  /// e.g. “TSLA”
  final String ticker;

  /// URL or asset path to your logo
  final String logoUrl;

  /// Current share price, e.g. 340.15
  final double currentPrice;

  /// Absolute change, e.g. –9.83
  final double priceChange;

  /// Percent change, e.g. –2.81
  final double priceChangePercent;

  /// Expiry date of the option
  final DateTime expiryDate;

  /// Strike price, e.g. 340
  final double strikePrice;

  /// Odds for “Over”
  final double overOdds;

  /// Odds for “Under”
  final double underOdds;

  String get priceChangeAndPricePercentChange {
    return "$priceChange ($priceChangePercent)";
  }

  String get expiryDateFormatted {
    return formatDateTimeToMMDDYYYY(expiryDate);
  }

  TrendingBetModel({
    required this.companyName,
    required this.ticker,
    required this.logoUrl,
    required this.currentPrice,
    required this.priceChange,
    required this.priceChangePercent,
    required this.expiryDate,
    required this.strikePrice,
    required this.overOdds,
    required this.underOdds,
  });

  /// Create one from JSON (e.g. from your API)
  factory TrendingBetModel.fromJson(Map<String, dynamic> json) {
    return TrendingBetModel(
      companyName: json['companyName'] as String,
      ticker: json['ticker'] as String,
      logoUrl: json['logoUrl'] as String,
      currentPrice: (json['currentPrice'] as num).toDouble(),
      priceChange: (json['priceChange'] as num).toDouble(),
      priceChangePercent: (json['priceChangePercent'] as num).toDouble(),
      expiryDate: DateTime.parse(json['expiryDate'] as String),
      strikePrice: (json['strikePrice'] as num).toDouble(),
      overOdds: (json['overOdds'] as num).toDouble(),
      underOdds: (json['underOdds'] as num).toDouble(),
    );
  }

  /// Convert back to JSON
  Map<String, dynamic> toJson() => {
        'companyName': companyName,
        'ticker': ticker,
        'logoUrl': logoUrl,
        'currentPrice': currentPrice,
        'priceChange': priceChange,
        'priceChangePercent': priceChangePercent,
        'expiryDate': expiryDate.toIso8601String(),
        'strikePrice': strikePrice,
        'overOdds': overOdds,
        'underOdds': underOdds,
      };
}
