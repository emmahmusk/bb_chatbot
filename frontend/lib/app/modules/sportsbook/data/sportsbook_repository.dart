import 'dart:convert';

import 'package:frontend/app/shared/classes/http/http.dart';
import 'package:http/http.dart' as dart_http;

import 'sportsbook_models.dart';

class SportsbookRepository {
  final HTTP http;

  SportsbookRepository(this.http);

  bool get _demoMode => http.sportsbookMode == 'demo';

  String get _demoBase => http.chatbotBaseUrl.trim().replaceFirst(RegExp(r'/+$'), '');

  dynamic _decode(dart_http.Response response, String fallback) {
    final text = utf8.decode(response.bodyBytes).trim();
    try {
      return jsonDecode(text);
    } on FormatException {
      // CloudFront/S3 and reverse proxies sometimes return an HTML/XML error
      // document. Do not expose the parser exception to users; report the
      // actual endpoint failure instead.
      throw Exception(response.statusCode >= 400
          ? '$fallback (HTTP ${response.statusCode})'
          : '$fallback returned a non-JSON response. Check the API base URL.');
    }
  }

  Future<Map<String, dynamic>> _get(String endpoint, {Map<String, String>? query, String? overrideBaseUrl}) async {
    final response = await http.get(endpoint, overrideBaseUrl: overrideBaseUrl, queryParameters: query);
    final body = _decode(response, 'Unable to load sportsbook data.');
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception((body is Map ? body['detail'] ?? body['message'] : null) ?? 'Unable to load sportsbook data.');
    }
    return Map<String, dynamic>.from(body as Map);
  }

  Future<Map<String, dynamic>> _preferChatbotDemo(
    Map<String, dynamic> body,
    String endpoint, {
    Map<String, String>? query,
  }) async {
    // The EC2 API deliberately returns HTTP 200 with demo: true when its
    // OpticOdds key is expired. Prefer the operator-edited Demo Odds Lab in
    // that case, but retain the server response if the chatbot is unavailable.
    if (_demoMode || body['demo'] != true || _demoBase.isEmpty) return body;
    try {
      return await _get(endpoint, overrideBaseUrl: _demoBase, query: query);
    } catch (_) {
      return body;
    }
  }

  Future<Map<String, dynamic>> _post(String endpoint, Map<String, dynamic> payload, {String? overrideBaseUrl}) async {
    final response = await http.post(endpoint, overrideBaseUrl: overrideBaseUrl, body: payload);
    final body = _decode(response, 'Unable to record the bet.');
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception((body is Map ? body['detail'] ?? body['message'] : null) ?? 'Unable to record the bet.');
    }
    return Map<String, dynamic>.from(body as Map);
  }

  Future<(List<SportsbookSport>, List<SportsbookProvider>)> catalog() async {
    Map<String, dynamic> body;
    try {
      body = _demoMode && _demoBase.isNotEmpty
          ? await _get('api/demo-odds-lab/sports/', overrideBaseUrl: _demoBase)
          : await _get('bet/sportsbook/catalog/');
      body = await _preferChatbotDemo(body, 'api/demo-odds-lab/sports/');
    } catch (_) {
      // Keep the public sportsbook usable while the live API/key is down.
      // The chatbot service owns a local, deterministic demo catalog for this
      // exact purpose and does not call OpticOdds.
      final bridgeBase = _demoBase;
      if (bridgeBase.isEmpty) return (_demoSports(), const [SportsbookProvider(id: 'draftkings', name: 'DraftKings')]);
      try {
        body = await _get('api/demo-odds-lab/sports/', overrideBaseUrl: bridgeBase);
      } catch (_) {
        return (_demoSports(), const [SportsbookProvider(id: 'draftkings', name: 'DraftKings')]);
      }
    }
    final sports = (body['sports'] as List? ?? []).whereType<Map>().map((item) => SportsbookSport.fromJson(Map<String, dynamic>.from(item))).where((item) => item.id.isNotEmpty).toList();
    if (sports.isEmpty) return (_demoSports(), const [SportsbookProvider(id: 'draftkings', name: 'DraftKings')]);
    // Peer books are intentionally hidden from the betting experience. The
    // chatbot monitor adds its saved comparison books server-side when the
    // betslip is recorded.
    return (sports, const [SportsbookProvider(id: 'draftkings', name: 'DraftKings')]);
  }

  Future<List<SportsbookLeague>> leagues(String sport) async {
    Map<String, dynamic> body;
    final query = {'sport': Uri.encodeQueryComponent(sport)};
    try {
      body = _demoMode && _demoBase.isNotEmpty
          ? await _get('api/demo-odds-lab/leagues/', overrideBaseUrl: _demoBase, query: query)
          : await _get('bet/sportsbook/leagues/', query: query);
      body = await _preferChatbotDemo(body, 'api/demo-odds-lab/leagues/', query: query);
    } catch (_) {
      final bridgeBase = _demoBase;
      if (bridgeBase.isEmpty) return _demoLeagues(sport);
      try {
        body = await _get('api/demo-odds-lab/leagues/', overrideBaseUrl: bridgeBase, query: query);
      } catch (_) {
        return _demoLeagues(sport);
      }
    }
    return (body['leagues'] as List? ?? []).whereType<Map>().map((item) => SportsbookLeague.fromJson(Map<String, dynamic>.from(item))).where((item) => item.id.isNotEmpty).toList();
  }

  Future<List<SportsbookFixture>> fixtures(String sport, String league) async {
    Map<String, dynamic> body;
    final query = {'sport': Uri.encodeQueryComponent(sport), 'league': Uri.encodeQueryComponent(league)};
    try {
      body = _demoMode && _demoBase.isNotEmpty
          ? await _get('api/demo-odds-lab/fixtures/', overrideBaseUrl: _demoBase, query: query)
          : await _get('bet/sportsbook/fixtures/', query: query);
      body = await _preferChatbotDemo(body, 'api/demo-odds-lab/fixtures/', query: query);
    } catch (_) {
      final bridgeBase = _demoBase;
      if (bridgeBase.isEmpty) return _demoFixtures(sport, league);
      try {
        body = await _get('api/demo-odds-lab/fixtures/', overrideBaseUrl: bridgeBase, query: query);
      } catch (_) {
        return _demoFixtures(sport, league);
      }
    }
    return (body['fixtures'] as List? ?? []).whereType<Map>().map((item) => SportsbookFixture.fromJson(Map<String, dynamic>.from(item))).where((item) => item.id.isNotEmpty).toList();
  }

  Future<List<SportsbookOdd>> odds(String fixtureId, String market, List<SportsbookProvider> providers) async {
    Map<String, dynamic> body;
    final query = {'market': Uri.encodeQueryComponent(market), 'sportsbooks': providers.map((item) => item.id).join(',')};
    try {
      body = _demoMode && _demoBase.isNotEmpty
          ? await _get('api/demo-odds-lab/fixtures/${Uri.encodeComponent(fixtureId)}/odds/', overrideBaseUrl: _demoBase, query: query)
          : await _get('bet/sportsbook/fixtures/${Uri.encodeComponent(fixtureId)}/odds/', query: query);
      body = await _preferChatbotDemo(body, 'api/demo-odds-lab/fixtures/${Uri.encodeComponent(fixtureId)}/odds/', query: query);
    } catch (_) {
      final bridgeBase = _demoBase;
      if (bridgeBase.isEmpty) return _demoOdds(fixtureId, market, providers);
      try {
        body = await _get('api/demo-odds-lab/fixtures/${Uri.encodeComponent(fixtureId)}/odds/', overrideBaseUrl: bridgeBase, query: query);
      } catch (_) {
        return _demoOdds(fixtureId, market, providers);
      }
    }
    return (body['odds'] as List? ?? []).whereType<Map>().map((item) => SportsbookOdd.fromJson(Map<String, dynamic>.from(item))).where((item) => item.decimal > 1).toList();
  }

  Future<Map<String, dynamic>> recordBetSlip({required double stake, required List<SportsbookSelection> selections}) {
    // When configured, route placement through the chatbot service. It reads
    // the comparison books saved in the monitor settings and forwards the
    // authenticated betslip to the EC2 API. The direct server route remains a
    // safe fallback for local development.
    final payload = {'stake': stake, 'legs': selections.map((selection) => selection.toJson()).toList()};
    final bridgeBase = http.chatbotBaseUrl.trim().replaceFirst(RegExp(r'/+$'), '');
    if (bridgeBase.isNotEmpty) {
      return _post('api/admin-sportsbook/betslips', payload, overrideBaseUrl: bridgeBase);
    }
    return _post('bet/sportsbook/betslips', payload);
  }

  List<SportsbookSport> _demoSports() => const [
        SportsbookSport(id: 'soccer', name: 'Soccer'),
        SportsbookSport(id: 'basketball', name: 'Basketball'),
        SportsbookSport(id: 'baseball', name: 'Baseball'),
        SportsbookSport(id: 'football', name: 'Football'),
        SportsbookSport(id: 'hockey', name: 'Hockey'),
        SportsbookSport(id: 'tennis', name: 'Tennis'),
      ];

  List<SportsbookLeague> _demoLeagues(String sport) {
    const names = {'soccer': 'England - Premier League', 'basketball': 'NBA', 'baseball': 'MLB', 'football': 'NFL', 'hockey': 'NHL', 'tennis': 'ATP'};
    final id = sport.toLowerCase();
    return [SportsbookLeague(id: id == 'soccer' ? 'england_-_premier_league' : id, name: names[id] ?? 'Demo League')];
  }

  List<SportsbookFixture> _demoFixtures(String sport, String league) {
    const teams = {
      'soccer': [('Arsenal FC', 'Chelsea FC'), ('Liverpool FC', 'Everton FC'), ('Leeds United FC', 'Aston Villa FC'), ('Brighton & Hove Albion FC', 'Sunderland AFC'), ('Newcastle United FC', 'Tottenham Hotspur FC')],
      'basketball': [('Boston Celtics', 'Los Angeles Lakers'), ('Denver Nuggets', 'Phoenix Suns'), ('New York Knicks', 'Milwaukee Bucks'), ('Golden State Warriors', 'Dallas Mavericks'), ('Miami Heat', 'Chicago Bulls')],
      'baseball': [('New York Yankees', 'Boston Red Sox'), ('Los Angeles Dodgers', 'San Diego Padres'), ('Atlanta Braves', 'New York Mets'), ('Chicago Cubs', 'St. Louis Cardinals'), ('Philadelphia Phillies', 'Washington Nationals')],
      'football': [('Kansas City Chiefs', 'Buffalo Bills'), ('Dallas Cowboys', 'Philadelphia Eagles'), ('San Francisco 49ers', 'Seattle Seahawks'), ('Baltimore Ravens', 'Cincinnati Bengals'), ('Green Bay Packers', 'Chicago Bears')],
      'hockey': [('Toronto Maple Leafs', 'Montreal Canadiens'), ('Boston Bruins', 'New York Rangers'), ('Edmonton Oilers', 'Vancouver Canucks'), ('Colorado Avalanche', 'Dallas Stars'), ('Florida Panthers', 'Tampa Bay Lightning')],
      'tennis': [('Carlos Alcaraz', 'Jannik Sinner'), ('Aryna Sabalenka', 'Iga Swiatek'), ('Novak Djokovic', 'Alexander Zverev'), ('Coco Gauff', 'Elena Rybakina'), ('Daniil Medvedev', 'Taylor Fritz')],
    };
    final selected = teams[sport.toLowerCase()] ?? teams['soccer']!;
    final now = DateTime.now().toUtc();
    return [
      for (var index = 0; index < selected.length; index++)
        SportsbookFixture(id: 'demo-${sport.toLowerCase()}-${(index + 1).toString().padLeft(3, '0')}', event: '${selected[index].$2} @ ${selected[index].$1}', homeTeam: selected[index].$1, awayTeam: selected[index].$2, sport: sport, league: league, startDate: now.add(Duration(days: index + 1)), isLive: false),
    ];
  }

  List<SportsbookOdd> _demoOdds(String fixtureId, String market, List<SportsbookProvider> providers) {
    final parts = fixtureId.split('-');
    final sport = parts.length > 1 ? parts[1] : 'soccer';
    final index = parts.length > 2 ? (int.tryParse(parts[2]) ?? 1) - 1 : 0;
    final fixture = _demoFixtures(sport, sport).elementAt(index.clamp(0, 4).toInt());
    final selections = sport == 'soccer' ? [fixture.homeTeam, 'Draw', fixture.awayTeam] : [fixture.homeTeam, fixture.awayTeam];
    final base = sport == 'soccer' ? [1.75, 3.60, 2.15] : [1.78, 2.08];
    final rows = <SportsbookOdd>[];
    for (final provider in providers) {
      for (var selectionIndex = 0; selectionIndex < selections.length; selectionIndex++) {
        final decimal = base[selectionIndex] + ((index + selectionIndex) % 3) * 0.01;
        rows.add(SportsbookOdd(fixtureId: fixtureId, event: fixture.event, sport: sport, league: sport, sportsbook: provider.id, market: market, selection: selections[selectionIndex], price: _demoAmerican(decimal), decimal: decimal));
      }
    }
    return rows;
  }

  String _demoAmerican(double decimal) => decimal >= 2 ? '+${((decimal - 1) * 100).round()}' : '-${(100 / (decimal - 1)).round()}';
}
