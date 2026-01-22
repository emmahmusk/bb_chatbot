class VisitedStockModel {
  final String imageUrl;
  final String companyName;
  final String symbol;
  final String expiry;
  final int id;

  VisitedStockModel({
    required this.imageUrl,
    required this.companyName,
    required this.symbol,
    required this.expiry,
    required this.id,
  });

  Map<String, dynamic> toJson() => {
        'imageUrl': imageUrl,
        'companyName': companyName,
        'symbol': symbol,
        'expiry': expiry,
        'id': id,
      };

  factory VisitedStockModel.fromJson(Map<String, dynamic> json) {
    return VisitedStockModel(
      imageUrl: json['imageUrl'],
      companyName: json['companyName'],
      symbol: json['symbol'],
      expiry: json['expiry'],
      id: json['id'],
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) || (other is VisitedStockModel && other.id == id);

  @override
  int get hashCode => id.hashCode;
}
