class SingleBetDto {
  /// ID of the market you’re betting on.
  final int marketId;

  /// Either `"over"` or `"under"`.
  final String chosenOutcome;

  /// How much the user wagers, as a number.
  final double amountWagered;

  SingleBetDto({
    required this.marketId,
    required this.chosenOutcome,
    required this.amountWagered,
  });

  Map<String, dynamic> toJson() => {
        'market_id': marketId,
        'chosen_outcome': chosenOutcome,
        'amount_wagered': amountWagered,
      };
}
