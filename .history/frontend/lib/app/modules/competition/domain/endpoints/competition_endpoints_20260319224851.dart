class CompetitionEndpoints {
  static const String base = 'bet/competitions';

  static String detail(int competitionId) => '$base/$competitionId';
  static String join(int competitionId) => '$base/$competitionId/join';
  static String leaderboard(int competitionId) => '$base/$competitionId/leaderboard';
  static String myCompetitions() => '$base/my';
}
