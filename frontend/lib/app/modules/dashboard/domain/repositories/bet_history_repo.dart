import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../../data/models/bet_history_model.dart';

class BetHistoryRepository {
  Future<List<BetHistoryModel>> getBetHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');

    final headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };

    final uri = Uri.parse("https://api.bbbprediction.com/users/bet_history/");
    final res = await http.get(uri, headers: headers);

    if (res.statusCode == 200) {
      final List decoded = json.decode(res.body);
      return decoded.map((e) => BetHistoryModel.fromJson(e)).toList();
    } else {
      throw Exception("Failed to load bet history");
    }
  }
}