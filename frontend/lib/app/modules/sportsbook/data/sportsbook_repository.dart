import 'dart:convert';

import 'package:frontend/app/shared/classes/http/http.dart';

import 'sportsbook_models.dart';

class SportsbookRepository {
  final HTTP http;

  SportsbookRepository(this.http);

  Future<Map<String, dynamic>> _get(String endpoint, {Map<String, String>? query}) async {
    final response = await http.get(endpoint, queryParameters: query);
    final body = jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception((body is Map ? body['detail'] ?? body['message'] : null) ?? 'Unable to load sportsbook data.');
    }
    return Map<String, dynamic>.from(body as Map);
  }

  Future<Map<String, dynamic>> _post(String endpoint, Map<String, dynamic> payload, {String? overrideBaseUrl}) async {
    final response = await http.post(endpoint, overrideBaseUrl: overrideBaseUrl, body: payload);
    final body = jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception((body is Map ? body['detail'] ?? body['message'] : null) ?? 'Unable to record the bet.');
    }
    return Map<String, dynamic>.from(body as Map);
  }

  Future<(List<SportsbookSport>, List<SportsbookProvider>)> catalog() async {
    final body = await _get('bet/sportsbook/catalog/');
    final sports = (body['sports'] as List? ?? []).whereType<Map>().map((item) => SportsbookSport.fromJson(Map<String, dynamic>.from(item))).where((item) => item.id.isNotEmpty).toList();
    // Peer books are intentionally hidden from the betting experience. The
    // chatbot monitor adds its saved comparison books server-side when the
    // betslip is recorded.
    return (sports, const [SportsbookProvider(id: 'draftkings', name: 'DraftKings')]);
  }

  Future<List<SportsbookLeague>> leagues(String sport) async {
    final body = await _get('bet/sportsbook/leagues/', query: {'sport': Uri.encodeQueryComponent(sport)});
    return (body['leagues'] as List? ?? []).whereType<Map>().map((item) => SportsbookLeague.fromJson(Map<String, dynamic>.from(item))).where((item) => item.id.isNotEmpty).toList();
  }

  Future<List<SportsbookFixture>> fixtures(String sport, String league) async {
    final body = await _get('bet/sportsbook/fixtures/', query: {'sport': Uri.encodeQueryComponent(sport), 'league': Uri.encodeQueryComponent(league)});
    return (body['fixtures'] as List? ?? []).whereType<Map>().map((item) => SportsbookFixture.fromJson(Map<String, dynamic>.from(item))).where((item) => item.id.isNotEmpty).toList();
  }

  Future<List<SportsbookOdd>> odds(String fixtureId, String market, List<SportsbookProvider> providers) async {
    final body = await _get('bet/sportsbook/fixtures/${Uri.encodeComponent(fixtureId)}/odds/', query: {'market': Uri.encodeQueryComponent(market), 'sportsbooks': providers.map((item) => item.id).join(',')});
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
}
