class ParlayBetDto {
  /// As per your API, we keep this as a string so it’s serialized as `"500.00"`.
  final String amountWagered;

  /// One entry per leg in your parlay.
  final List<ParlayLegDto> legs;

  ParlayBetDto({
    required this.amountWagered,
    required this.legs,
  });

  /// Factory to build from raw values if you like:
  factory ParlayBetDto.fromValues({
    required double wagerAmount,
    required List<ParlayLegDto> legs,
  }) {
    // Format to two decimals
    final amt = wagerAmount.toStringAsFixed(2);
    return ParlayBetDto(amountWagered: amt, legs: legs);
  }

  Map<String, dynamic> toJson() => {
        'amount_wagered': amountWagered,
        'legs': legs.map((leg) => leg.toJson()).toList(),
      };
}

class ParlayLegDto {
  final int marketId;
  final String chosenOutcome;

  ParlayLegDto({
    required this.marketId,
    required this.chosenOutcome,
  });

  Map<String, dynamic> toJson() => {
        'market_id': marketId,
        'chosen_outcome': chosenOutcome,
      };
}
