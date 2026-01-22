import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/data/models/market_model_new.dart';
import 'package:frontend/app/shared/classes/http/http.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';
import 'dart:convert'; // make sure this is imported

final dashboardRepositoryNewProvider = Provider((ref) {
  final http = ref.read(httpProvider);
  return DashboardRepositoryNew(http: http);
});

class DashboardRepositoryNew {
  final HTTP http;

  DashboardRepositoryNew({required this.http});

//   Future<AppState<List<MarketModel>>> getMarkets() async {
//   try {
//     final response = await http.get('bet/markets/?trending=true');

//     print("Chethan P S S");

//     print("Status Code: ${response.statusCode}");
//      print("Raw response type: ${response.runtimeType}");
//     print("Raw body: ${response.body}");
//     print(response.request);
//     // Try decoding only if it's a string
//     final rawBody = response.body;
//     final decoded = rawBody is String ? json.decode(rawBody) : rawBody;

//     if (decoded is List) {
//       final list = decoded.map((e) => MarketModel.fromJson(e)).toList();
//       return AppState.success(list);
//     } else {
//       return AppState.error("Unexpected data format: $decoded");
//     }
//   } catch (e) {
//     return AppState.error("Error decoding markets: $e");
//   }
// }

  Future<AppState<PaginatedMarketModel>> getMarkets({Map<String, String>? queryParams}) async {
  try {
     String url = 'bet/markets';

      final params = {
        'page': '1',
        ...?queryParams,
      };

      final filtered = params.entries
          .where((e) => e.key.trim().isNotEmpty && e.value.trim().isNotEmpty)
          .map((e) => '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}')
          .join('&');

      // Start with base URL and query params
      if (filtered.isNotEmpty) {
        url += '?$filtered';

        // ✅ Add trailing slash ONLY if trending or expiring_soon present
        // if (params.containsKey('trending') || params.containsKey('expiring_soon')) {
        //   url += '/';
        // }
      }

      // ✅ Log message for "All Stocks"
    // final isAllStocks = (queryParams == null || queryParams.isEmpty || (queryParams.keys.toSet().intersection({
    //   'trending' , 'expiring_soon' 
    // }).isEmpty));

    // if (isAllStocks) {
    //   print("✅ [Frontend] Fetching ALL STOCKS Called");
    // } else {
    //   print("✅ [Frontend] Fetching FILTERED STOCKS with query: $queryParams");
    // }
    // print("Chethan - queryParams");
    // print(queryParams);
    final response = await http.get(url );

    final rawBody = response.body;
    // print("Chethan Response");
    // print(rawBody);

    // print("Request url");
    // print(response.request);
    var decoded = rawBody is String ? json.decode(rawBody) : rawBody;
    // print("Chethan Decoded");
    final paginated;
    // if(queryParams==null){
       
    //   final results = decoded['results'] as List<dynamic>;

    //   // Sort ascending
    //   results.sort((a, b) => a['stock']['company_name']
    //       .toString()
    //       .toLowerCase()
    //       .compareTo(b['stock']['company_name'].toString().toLowerCase()));

    //   // If descending, use:
    //   // results.sort((a, b) => b['stock']['company_name']
    //   //     .toString()
    //   //     .toLowerCase()
    //   //     .compareTo(a['stock']['company_name'].toString().toLowerCase()));

    //   // Reassign sorted list back to decoded
    //   decoded['results'] = results;
    // } 
      paginated = PaginatedMarketModel.fromJson(decoded);
    
     
    return AppState.success(paginated);
 
  } catch (e) {
    return AppState.error("Error decoding markets: $e");
  }
}

}
