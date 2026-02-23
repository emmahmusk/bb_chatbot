import 'package:frontend/app/shared/functions/date_functions.dart';

class MarketModel {
  final int id;
  final String stockSymbol;
  final String? stockCompanyName;
  final double targetPrice;
  final DateTime expiryDate;
  final String outcomeType;
  final String displayOddsOver;
  final String displayOddsUnder;
  final bool isActive;
  final double? exposureOver;
  final double? exposureUnder;
  final bool requiresAdminOverride;
  final DateTime createdAt;
  final DateTime updatedAt;

  MarketModel({
    required this.id,
    required this.stockSymbol,
    this.stockCompanyName,
    required this.targetPrice,
    required this.expiryDate,
    required this.outcomeType,
    required this.displayOddsOver,
    required this.displayOddsUnder,
    required this.isActive,
    this.exposureOver,
    this.exposureUnder,
    this.requiresAdminOverride = false,
    required this.createdAt,
    required this.updatedAt,
  });

  String get expiryDateFormatted => expiryDate.toShortDate();

  MarketModel copyWith({
    int? id,
    String? stockSymbol,
    String? stockCompanyName,
    double? targetPrice,
    DateTime? expiryDate,
    String? outcomeType,
    String? displayOddsOver,
    String? displayOddsUnder,
    bool? isActive,
    double? exposureOver,
    double? exposureUnder,
    bool? requiresAdminOverride,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return MarketModel(
      id: id ?? this.id,
      stockSymbol: stockSymbol ?? this.stockSymbol,
      stockCompanyName: stockCompanyName ?? this.stockCompanyName,
      targetPrice: targetPrice ?? this.targetPrice,
      expiryDate: expiryDate ?? this.expiryDate,
      outcomeType: outcomeType ?? this.outcomeType,
      displayOddsOver: displayOddsOver ?? this.displayOddsOver,
      displayOddsUnder: displayOddsUnder ?? this.displayOddsUnder,
      isActive: isActive ?? this.isActive,
      exposureOver: exposureOver ?? this.exposureOver,
      exposureUnder: exposureUnder ?? this.exposureUnder,
      requiresAdminOverride: requiresAdminOverride ?? this.requiresAdminOverride,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  factory MarketModel.fromJson(Map<String, dynamic> json) {
    return MarketModel(
      id: json['id'] as int,
      stockSymbol: json['stock_symbol'] as String,
      stockCompanyName: json['stock_company_name'] as String?,
      targetPrice: double.parse(json['target_price'] as String),
      expiryDate: DateTime.parse(json['expiry_date'] as String),
      outcomeType: json['outcome_type'] as String,
      displayOddsOver: json['display_odds_over'] as String,
      displayOddsUnder: json['display_odds_under'] as String,
      isActive: json['is_active'] as bool,
      exposureOver: json['exposure_over'] != null ? double.tryParse(json['exposure_over'].toString()) : null,
      exposureUnder: json['exposure_under'] != null ? double.tryParse(json['exposure_under'].toString()) : null,
      requiresAdminOverride: json['requires_admin_override'] == true,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'stock_symbol': stockSymbol,
        'stock_company_name': stockCompanyName,
        'target_price': targetPrice.toStringAsFixed(2),
        'expiry_date': expiryDate.toIso8601String().split('T').first,
        'outcome_type': outcomeType,
        'display_odds_over': displayOddsOver,
        'display_odds_under': displayOddsUnder,
        'is_active': isActive,
      'exposure_over': exposureOver,
      'exposure_under': exposureUnder,
      'requires_admin_override': requiresAdminOverride,
        'created_at': createdAt.toUtc().toIso8601String(),
        'updated_at': updatedAt.toUtc().toIso8601String(),
      };
}
