import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/competition/data/models/competition_models.dart';
import 'package:frontend/app/modules/competition/domain/endpoints/competition_endpoints.dart';
import 'package:frontend/app/shared/classes/http/http.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';

final competitionRepositoryProvider = Provider((ref) {
  final http = ref.read(httpProvider);
  return CompetitionRepository(http: http);
});

class CompetitionRepository {
  final HTTP http;

  CompetitionRepository({required this.http});

  Future<AppState<PaginatedCompetitionModel>> getCompetitions({
    Map<String, String>? queryParams,
  }) async {
    try {
      final response = await http.get(
        CompetitionEndpoints.base,
        queryParameters: queryParams,
      );
      final decoded = json.decode(response.body);

      if (response.statusCode == 200) {
        return AppState.success(PaginatedCompetitionModel.fromJson(decoded));
      }

      return AppState.error(_extractError(decoded));
    } catch (e) {
      return AppState.error('Failed to load competitions: $e');
    }
  }

  Future<AppState<CompetitionModel>> getCompetitionDetail(int competitionId) async {
    try {
      final response = await http.get(CompetitionEndpoints.detail(competitionId));
      final decoded = json.decode(response.body);

      if (response.statusCode == 200) {
        return AppState.success(CompetitionModel.fromJson(decoded));
      }

      return AppState.error(_extractError(decoded));
    } catch (e) {
      return AppState.error('Failed to load competition details: $e');
    }
  }

  Future<AppState<PaginatedCompetitionLeaderboardModel>> getLeaderboard(
    int competitionId,
    {
    Map<String, String>? queryParams,
    }
  ) async {
    try {
      final response = await http.get(
        CompetitionEndpoints.leaderboard(competitionId),
        queryParameters: queryParams,
      );
      final decoded = json.decode(response.body);

      if (response.statusCode == 200) {
        return AppState.success(
          PaginatedCompetitionLeaderboardModel.fromJson(decoded),
        );
      }

      return AppState.error(_extractError(decoded));
    } catch (e) {
      return AppState.error('Failed to load leaderboard: $e');
    }
  }

  Future<AppState<PaginatedCompetitionMembershipModel>> getMyCompetitions({
    Map<String, String>? queryParams,
  }) async {
    try {
      final response = await http.get(
        CompetitionEndpoints.myCompetitions(),
        queryParameters: queryParams,
      );
      final decoded = json.decode(response.body);

      if (response.statusCode == 200) {
        return AppState.success(
          PaginatedCompetitionMembershipModel.fromJson(decoded),
        );
      }

      return AppState.error(_extractError(decoded));
    } catch (e) {
      return AppState.error('Failed to load my competitions: $e');
    }
  }

  Future<AppState<JoinCompetitionResult>> joinCompetition(int competitionId) async {
    try {
      final response = await http.post(
        CompetitionEndpoints.join(competitionId),
        body: {},
      );
      final decoded = json.decode(response.body);

      if (response.statusCode == 200 || response.statusCode == 201) {
        return AppState.success(JoinCompetitionResult.fromJson(decoded));
      }

      return AppState.error(_extractError(decoded));
    } catch (e) {
      return AppState.error('Failed to join competition: $e');
    }
  }

  Future<AppState<CompetitionModel>> createCompetition(
    CompetitionCreateInput payload,
  ) async {
    try {
      final response = await http.post(
        CompetitionEndpoints.base,
        body: payload.toJson(),
      );
      final decoded = json.decode(response.body);

      if (response.statusCode == 201) {
        return AppState.success(CompetitionModel.fromJson(decoded));
      }

      return AppState.error(_extractError(decoded));
    } catch (e) {
      return AppState.error('Failed to create competition: $e');
    }
  }

  String _extractError(dynamic decoded) {
    if (decoded is! Map<String, dynamic>) {
      return 'Something went wrong';
    }

    if (decoded['error'] != null) {
      return decoded['error'].toString();
    }

    if (decoded['detail'] != null) {
      return decoded['detail'].toString();
    }

    for (final entry in decoded.entries) {
      final value = entry.value;
      if (value is List && value.isNotEmpty) {
        return value.first.toString();
      }
      if (value is String && value.isNotEmpty) {
        return value;
      }
    }

    return 'Something went wrong';
  }
}
