import 'package:frontend/app/modules/dashboard/data/models/market_details.dart';

class ParlayBetModel {
  final int id;
  final int user;
  final String amountWagered;
  final String combinedOdds;
  final String status;
  final String? payoutAmount;
  final List<ParlayLegModel> legs;
  final DateTime createdAt;

  ParlayBetModel({
    required this.id,
    required this.user,
    required this.amountWagered,
    required this.combinedOdds,
    required this.status,
    required this.payoutAmount,
    required this.legs,
    required this.createdAt,
  });

  factory ParlayBetModel.fromJson(Map<String, dynamic> json) {
    return ParlayBetModel(
      id: json['id'],
      user: json['user'],
      amountWagered: json['amount_wagered'],
      combinedOdds: json['combined_odds'],
      status: json['status'],
      payoutAmount: json['payout_amount'],
      legs: List<ParlayLegModel>.from(
        json['legs'].map((x) => ParlayLegModel.fromJson(x)),
      ),
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class ParlayLegModel {
  final int id;
  final String username;
  final MarketDetails marketDetails;
  final String amountWagered;
  final String oddsAtPlacement;
  final String chosenOutcome;
  final String status;
  final String? payoutAmount;
  final bool isParlayLeg;
  final int parlayBet;
  final DateTime createdAt;

  ParlayLegModel({
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

  factory ParlayLegModel.fromJson(Map<String, dynamic> json) {
    return ParlayLegModel(
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
