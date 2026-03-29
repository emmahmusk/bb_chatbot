class CompetitionModel {
  final int id;
  final String name;
  final String? description;
  final int? creator;
  final String? creatorUsername;
  final int maxMembers;
  final int memberCount;
  final DateTime? startDate;
  final DateTime? endDate;
  final DateTime? registrationCloseDate;
  final String status;
  final String entryFee;
  final String firstPlacePrize;
  final String secondPlacePrize;
  final String thirdPlacePrize;
  final String scoringMethod;
  final bool isPrivate;
  final bool isRegistrationOpen;
  final bool isFull;
  final bool userJoined;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const CompetitionModel({
    required this.id,
    required this.name,
    required this.description,
    required this.creator,
    required this.creatorUsername,
    required this.maxMembers,
    required this.memberCount,
    required this.startDate,
    required this.endDate,
    required this.registrationCloseDate,
    required this.status,
    required this.entryFee,
    required this.firstPlacePrize,
    required this.secondPlacePrize,
    required this.thirdPlacePrize,
    required this.scoringMethod,
    required this.isPrivate,
    required this.isRegistrationOpen,
    required this.isFull,
    required this.userJoined,
    required this.createdAt,
    required this.updatedAt,
  });

  factory CompetitionModel.fromJson(Map<String, dynamic> json) {
    DateTime? parseDate(dynamic value) {
      if (value == null) return null;
      return DateTime.tryParse(value.toString());
    }

    int parseInt(dynamic value, {int fallback = 0}) {
      if (value == null) return fallback;
      return int.tryParse(value.toString()) ?? fallback;
    }

    bool parseBool(dynamic value, {bool fallback = false}) {
      if (value is bool) return value;
      if (value == null) return fallback;
      final normalized = value.toString().toLowerCase();
      return normalized == 'true' || normalized == '1' || normalized == 'yes';
    }

    return CompetitionModel(
      id: parseInt(json['id']),
      name: json['name']?.toString() ?? '',
      description: json['description']?.toString(),
      creator: json['creator'] == null ? null : parseInt(json['creator']),
      creatorUsername: json['creator_username']?.toString(),
      maxMembers: parseInt(json['max_members']),
      memberCount: parseInt(json['member_count']),
      startDate: parseDate(json['start_date']),
      endDate: parseDate(json['end_date']),
      registrationCloseDate: parseDate(json['registration_close_date']),
      status: json['status']?.toString() ?? 'registration',
      entryFee: json['entry_fee']?.toString() ?? '0.00',
      firstPlacePrize: json['first_place_prize']?.toString() ?? '0.00',
      secondPlacePrize: json['second_place_prize']?.toString() ?? '0.00',
      thirdPlacePrize: json['third_place_prize']?.toString() ?? '0.00',
      scoringMethod: json['scoring_method']?.toString() ?? 'net_profit',
      isPrivate: parseBool(json['is_private']),
      isRegistrationOpen: parseBool(json['is_registration_open']),
      isFull: parseBool(json['is_full']),
      userJoined: parseBool(json['user_joined']),
      createdAt: parseDate(json['created_at']),
      updatedAt: parseDate(json['updated_at']),
    );
  }
}

class PaginatedCompetitionModel {
  final int count;
  final String? next;
  final String? previous;
  final List<CompetitionModel> results;

  const PaginatedCompetitionModel({
    required this.count,
    required this.next,
    required this.previous,
    required this.results,
  });

  factory PaginatedCompetitionModel.fromJson(Map<String, dynamic> json) {
    final resultList = (json['results'] as List<dynamic>? ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(CompetitionModel.fromJson)
        .toList();

    return PaginatedCompetitionModel(
      count: int.tryParse((json['count'] ?? 0).toString()) ?? 0,
      next: json['next']?.toString(),
      previous: json['previous']?.toString(),
      results: resultList,
    );
  }
}

class CompetitionMembershipModel {
  final int id;
  final int competition;
  final String competitionName;
  final int user;
  final String username;
  final DateTime? joinedAt;
  final int? finalRank;
  final String? finalScore;
  final bool isDisqualified;
  final String competitionCoinBalance;

  const CompetitionMembershipModel({
    required this.id,
    required this.competition,
    required this.competitionName,
    required this.user,
    required this.username,
    required this.joinedAt,
    required this.finalRank,
    required this.finalScore,
    required this.isDisqualified,
    required this.competitionCoinBalance,
  });

  factory CompetitionMembershipModel.fromJson(Map<String, dynamic> json) {
    return CompetitionMembershipModel(
      id: int.tryParse((json['id'] ?? 0).toString()) ?? 0,
      competition: int.tryParse((json['competition'] ?? 0).toString()) ?? 0,
      competitionName: json['competition_name']?.toString() ?? '',
      user: int.tryParse((json['user'] ?? 0).toString()) ?? 0,
      username: json['username']?.toString() ?? '',
      joinedAt: json['joined_at'] == null
          ? null
          : DateTime.tryParse(json['joined_at'].toString()),
      finalRank: json['final_rank'] == null
          ? null
          : int.tryParse(json['final_rank'].toString()),
      finalScore: json['final_score']?.toString(),
      isDisqualified: (json['is_disqualified'] ?? false) == true,
      competitionCoinBalance: json['competition_coin_balance']?.toString() ?? '0.00',
    );
  }
}

class PaginatedCompetitionMembershipModel {
  final int count;
  final String? next;
  final String? previous;
  final List<CompetitionMembershipModel> results;

  const PaginatedCompetitionMembershipModel({
    required this.count,
    required this.next,
    required this.previous,
    required this.results,
  });

  factory PaginatedCompetitionMembershipModel.fromJson(Map<String, dynamic> json) {
    final resultList = (json['results'] as List<dynamic>? ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(CompetitionMembershipModel.fromJson)
        .toList();

    return PaginatedCompetitionMembershipModel(
      count: int.tryParse((json['count'] ?? 0).toString()) ?? 0,
      next: json['next']?.toString(),
      previous: json['previous']?.toString(),
      results: resultList,
    );
  }
}

class CompetitionLeaderboardEntry {
  final int id;
  final int user;
  final String username;
  final DateTime? joinedAt;
  final int? finalRank;
  final String? finalScore;
  final num totalBets;
  final num netProfit;
  final num roi;
  final num winRate;

  const CompetitionLeaderboardEntry({
    required this.id,
    required this.user,
    required this.username,
    required this.joinedAt,
    required this.finalRank,
    required this.finalScore,
    required this.totalBets,
    required this.netProfit,
    required this.roi,
    required this.winRate,
  });

  factory CompetitionLeaderboardEntry.fromJson(Map<String, dynamic> json) {
    num parseNum(dynamic value) {
      if (value == null) return 0;
      return num.tryParse(value.toString()) ?? 0;
    }

    return CompetitionLeaderboardEntry(
      id: int.tryParse((json['id'] ?? 0).toString()) ?? 0,
      user: int.tryParse((json['user'] ?? 0).toString()) ?? 0,
      username: json['username']?.toString() ?? '',
      joinedAt: json['joined_at'] == null
          ? null
          : DateTime.tryParse(json['joined_at'].toString()),
      finalRank: json['final_rank'] == null
          ? null
          : int.tryParse(json['final_rank'].toString()),
      finalScore: json['final_score']?.toString(),
      totalBets: parseNum(json['total_bets']),
      netProfit: parseNum(json['net_profit']),
      roi: parseNum(json['roi']),
      winRate: parseNum(json['win_rate']),
    );
  }
}

class PaginatedCompetitionLeaderboardModel {
  final int count;
  final String? next;
  final String? previous;
  final List<CompetitionLeaderboardEntry> results;

  const PaginatedCompetitionLeaderboardModel({
    required this.count,
    required this.next,
    required this.previous,
    required this.results,
  });

  factory PaginatedCompetitionLeaderboardModel.fromJson(Map<String, dynamic> json) {
    final resultList = (json['results'] as List<dynamic>? ?? <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .map(CompetitionLeaderboardEntry.fromJson)
        .toList();

    return PaginatedCompetitionLeaderboardModel(
      count: int.tryParse((json['count'] ?? 0).toString()) ?? 0,
      next: json['next']?.toString(),
      previous: json['previous']?.toString(),
      results: resultList,
    );
  }
}

class JoinCompetitionResult {
  final int competitionId;
  final bool joined;
  final int currentMemberCount;
  final int maxMembers;
  final String message;
  final String remainingBbCashBalance;

  const JoinCompetitionResult({
    required this.competitionId,
    required this.joined,
    required this.currentMemberCount,
    required this.maxMembers,
    required this.message,
    required this.remainingBbCashBalance,
  });

  factory JoinCompetitionResult.fromJson(Map<String, dynamic> json) {
    bool parseBool(dynamic value, {bool fallback = false}) {
      if (value is bool) return value;
      if (value == null) return fallback;
      final normalized = value.toString().toLowerCase();
      return normalized == 'true' || normalized == '1' || normalized == 'yes';
    }

    return JoinCompetitionResult(
      competitionId: int.tryParse((json['competition_id'] ?? 0).toString()) ?? 0,
      joined: parseBool(json['joined']),
      currentMemberCount:
          int.tryParse((json['current_member_count'] ?? 0).toString()) ?? 0,
      maxMembers: int.tryParse((json['max_members'] ?? 0).toString()) ?? 0,
      message: json['message']?.toString() ?? '',
      remainingBbCashBalance:
          json['remaining_bb_cash_balance']?.toString() ?? '0.00',
    );
  }
}

class CompetitionCreateInput {
  final String name;
  final String description;
  final int maxMembers;
  final DateTime startDate;
  final DateTime endDate;
  final DateTime? registrationCloseDate;
  final String entryFee;
  final String firstPlacePrize;
  final String secondPlacePrize;
  final String thirdPlacePrize;
  final String scoringMethod;
  final bool isPrivate;
  final String startingCoinBalance;

  const CompetitionCreateInput({
    required this.name,
    required this.description,
    required this.maxMembers,
    required this.startDate,
    required this.endDate,
    required this.registrationCloseDate,
    required this.entryFee,
    required this.firstPlacePrize,
    required this.secondPlacePrize,
    required this.thirdPlacePrize,
    required this.scoringMethod,
    required this.isPrivate,
    required this.startingCoinBalance,
  });

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'description': description,
      'max_members': maxMembers,
      'start_date': startDate.toUtc().toIso8601String(),
      'end_date': endDate.toUtc().toIso8601String(),
      if (registrationCloseDate != null)
        'registration_close_date': registrationCloseDate!.toUtc().toIso8601String(),
      'entry_fee': entryFee,
      'first_place_prize': firstPlacePrize,
      'second_place_prize': secondPlacePrize,
      'third_place_prize': thirdPlacePrize,
      'scoring_method': scoringMethod,
      'is_private': isPrivate,
      'starting_coin_balance': startingCoinBalance,
    };
  }
}
