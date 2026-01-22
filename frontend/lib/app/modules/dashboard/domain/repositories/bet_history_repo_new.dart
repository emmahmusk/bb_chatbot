import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../../data/models/bet_history_model_new.dart';

class BetHistoryRepository {
  Future<List<BetHistoryModel>> fetchBetHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');

    final headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };

    final res = await http.get(
      Uri.parse('https://api.bbbprediction.com/users/bet_history'),
      headers: headers,
    );
    
    if (res.statusCode == 200) {
      final List<dynamic> data = json.decode(res.body);
      print("BET History");
      print(data);
      return data.map((json) => BetHistoryModel.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load bet history');
    }
  }
}
