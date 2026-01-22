import 'package:frontend/app/modules/dashboard/data/models/market_details.dart';

class SingleBetModel {
  final int id;
  final String username;
  final MarketDetails marketDetails;
  final String amountWagered;
  final String oddsAtPlacement;
  final String chosenOutcome;
  final String status;
  final String? payoutAmount;
  final bool isParlayLeg;
  final int? parlayBet;
  final DateTime createdAt;

  SingleBetModel({
    required this.id,
    required this.username,
    required this.marketDetails,
    required this.amountWagered,
    required this.oddsAtPlacement,
    required this.chosenOutcome,
    required this.status,
    required this.payoutAmount,
    required this.isParlayLeg,
    required this.parlayBet,
    required this.createdAt,
  });

  factory SingleBetModel.fromJson(Map<String, dynamic> json) {
    return SingleBetModel(
      id: json['id'],
      username: json['username'],
      marketDetails: MarketDetails.fromJson(json['market_details']),
      amountWagered: json['amount_wagered'],
      oddsAtPlacement: json['odds_at_placement'],
      chosenOutcome: json['chosen_outcome'],
      status: json['status'],
      payoutAmount: json['payout_amount'],
      isParlayLeg: json['is_parlay_leg'],
      parlayBet: json['parlay_bet'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}