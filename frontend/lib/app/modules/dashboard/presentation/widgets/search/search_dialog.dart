import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/presentation/widgets/search/tag.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_textfield.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/app/shared/presentation/widgets/loading_main_card.dart';
import 'package:http/http.dart' as http;
import 'dart:async';  
import 'package:go_router/go_router.dart';
import 'dart:convert'; 
import 'package:intl/intl.dart';
import 'package:frontend/app/modules/auth/presentation/providers/recently_visited_provider.dart';

class SearchDialog extends ConsumerStatefulWidget {
  const SearchDialog({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _SearchDialogState();
}

class _SearchDialogState extends ConsumerState<SearchDialog> {
  final searchController = TextEditingController();
  
  Timer? _debounce;
String? selectedTag;

  bool isTagsLoading = true;
  List<String> tags = [];

bool isMostViewedLoading = true;
List<Map<String, dynamic>> mostViewedResults = [];

  bool isLoading = false;
  List<Map<String, dynamic>> searchResults = [];


  final recentlyViewed = (
    "Recently Viewed",
    [
      (
        Pngs.tesla,
        "Tesla, Inc.",
        "\$TSLA",
      ),
      (
        Pngs.alphabet,
        "Alphabet Inc. (Google)",
        "\$GOOGL",
      ),
      (
        Pngs.airbnb,
        "Airbnb",
        "\$ABNB",
      ),
    ],
  );

  final mostViewed = (
    "Most viewed this week",
    [
      (
        Pngs.amazon,
        "Amazon",
        "\$AMZN",
      ),
      (
        Pngs.nvidia,
        "NVIDIA",
        "\$NVDA",
      ),
      (
        Pngs.meta,
        "META",
        "\$META",
      ),
    ],
  );

      @override
      void initState() {
        super.initState();
        searchController.addListener(_onSearchChanged);
         _fetchMostViewedResults(); 
         _fetchTags();
      }

      Future<void> _fetchTags() async {
        setState(() => isTagsLoading = true);
        final url = Uri.parse('https://api.bbbprediction.com/bet/stocks/search-with-tags/');
        try {
          final response = await http.get(url);
          if (response.statusCode == 200) {
            final data = jsonDecode(response.body) as Map<String, dynamic>;
            final fetched = (data['tags'] as List).cast<String>();
            setState(() {
              tags = fetched;
              isTagsLoading = false;
            });
          } else {
            debugPrint('Failed to load tags: ${response.statusCode}');
            setState(() => isTagsLoading = false);
          }
        } catch (e) {
          debugPrint('API Error (tags): $e');
          setState(() => isTagsLoading = false);
        }
      }


Future<void> _fetchMostViewedResults() async {
  setState(() {
    isMostViewedLoading = true;
  });

  final url = Uri.parse('https://api.bbbprediction.com/bet/markets/?most_viewed=true');
  try {
    final response = await http.get(url);

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      setState(() {
        mostViewedResults = List<Map<String, dynamic>>.from(json['results']);
        isMostViewedLoading = false;
      });
    } else {
      print('Failed to load most viewed: ${response.statusCode}');
      setState(() => isMostViewedLoading = false);
    }
  } catch (e) {
    print('API Error (most viewed): $e');
    setState(() => isMostViewedLoading = false);
  }
}

      @override
      void dispose() {
        searchController.removeListener(_onSearchChanged);
        searchController.dispose();
        _debounce?.cancel();
        super.dispose();
      }

      void _onSearchChanged() {
        if (_debounce?.isActive ?? false) _debounce!.cancel();
        _debounce = Timer(const Duration(milliseconds: 300), () {
          final query = searchController.text.trim().toUpperCase();
          if (query.isNotEmpty) {
            _fetchSearchResults(query);
          }
        });
      }
Future<void> _fetchSearchResults(String query) async {
  setState(() {
    isLoading = true;
    selectedTag="";
  });

  final url = Uri.parse('https://api.bbbprediction.com/bet/markets/?search=$query');
  try {
    final response = await http.get(url);

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      setState(() {
        searchResults = List<Map<String, dynamic>>.from(json['results']);
         
        isLoading = false;
      });
    } else {
      
      setState(() => isLoading = false);
    }
  } catch (e) {
    
    setState(() => isLoading = false);
  }
}


// List<(String, String, String, String)> _mapSearchResults() {
//   final seen = <String>{};
//   final output = <(String, String, String, String)>[];

//   for (final item in searchResults) {
//     final stock = item['stock'];
//     final symbol = stock['symbol'];
//     final name = stock['company_name'];
//     final imageUrl = stock['url'];
//     final expiry = item['expiry_date'];

//     if (!seen.contains(symbol)) {
//       seen.add(symbol);
//       output.add((imageUrl, name, symbol, expiry));
//     }
//   }

//   return output;
// }

List<(String, String, String, String, int)> _mapSearchResults() {
  final seen = <String>{};
  final output = <(String, String, String, String, int)>[];

  for (final item in searchResults) {
    final stock = item['stock'];
    final symbol = stock['symbol'];
    final name = stock['company_name'];
    final imageUrl = stock['url'];
    final expiry = item['expiry_date'];
    final id = item['id'];

    if ([symbol, name, imageUrl, expiry, id].any((x) => x == null)) continue;

    if (!seen.contains(symbol)) {
      seen.add(symbol);
      output.add((imageUrl, name, symbol, expiry, id));
    }
  }

  return output;
}

List<(String, String, String, String, int)> _mapMostViewedResults() {
  final seen = <String>{};
  final output = <(String, String, String, String, int)>[];

  for (final item in mostViewedResults) {
    final stock = item['stock'];
    final symbol = stock['symbol'];
    final name = stock['company_name'];
    final imageUrl = stock['url'];
    final expiry = item['expiry_date'];
    final id = item['id'] as int;

    if (!seen.contains(symbol)) {
      seen.add(symbol);
      output.add((imageUrl, name, symbol, expiry, id));
    }
  }

  return output;
}


Future<void> _fetchSearchByTag(String tag) async {
  setState(() {
    isLoading = true;
  });

  final url = Uri.parse('https://api.bbbprediction.com/bet/stocks/search-with-tags/?tag=$tag');
  try {
    final response = await http.get(url);
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      final List<dynamic> rawResults = json['results'] ?? [];

      final filtered = rawResults.where((item) =>
        item['symbol'] != null &&
        item['id'] != null &&
        item['expiry_date'] != null &&
        item['company_name'] != null &&
        item['url'] != null
      ).toList();

      setState(() {
        searchResults = List<Map<String, dynamic>>.from(filtered.map((e) => {
          "stock": {
            "symbol": e["symbol"],
            "company_name": e["company_name"],
            "url": e["url"],
          },
          "id": e["id"],
          "expiry_date": e["expiry_date"],
        }));
        isLoading = false;
      });

    } else {
      print('Failed to load tag search: ${response.statusCode}');
      setState(() => isLoading = false);
    }
  } catch (e) {
    print('API Error (tag search): $e');
    setState(() => isLoading = false);
  }
}


  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final viewport = MediaQuery.of(context).size;
    final isMobile = viewport.width < 600;
    return Container(
      width: isMobile ? viewport.width - 20 : 893,
      height: isMobile ? viewport.height - 120 : 500,
      padding: EdgeInsets.symmetric(vertical: isMobile ? 8 : 10),
      decoration: BoxDecoration(
        color: colors.always161B22,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: colors.always30363D.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CustomTextField(
            textEditingController: searchController,
            textFieldColor: colors.always161B22,
            hint: "Search 'Apple' ",
            prefix: Image.asset(
              Pngs.search,
              width: 20,
              height: 20,
              fit: BoxFit.cover,
            ),
            hasPrefixSpace: true,
            hasBorder: false,
          ),
          const SizedBox(height: 5),
          CustomDivider(),
          SizedBox(height: isMobile ? 12 : 16),
           Padding(
  padding: EdgeInsets.symmetric(horizontal: isMobile ? 16 : 20),
  child: isTagsLoading
      ? const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: LoadingMainCard(),
        )
      : Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final t in tags)
              GestureDetector(
                onTap: () {
                  setState(() => selectedTag = t);
                  _fetchSearchByTag(t);
                  // optional: also trigger search
                  // searchController.text = t;
                  // _fetchSearchResults(t.toUpperCase());
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      vertical: 6, horizontal: 12),
                  decoration: BoxDecoration(
                    color: selectedTag == t
                        ? Colors.white   // highlight if selected
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.6),
                    ),
                  ),
                  child: Text(
                    t,
                    style: TextStyle(
                      color: selectedTag == t
                          ? Colors.black
                          : Colors.white,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
          ],
        ),
        ),

        
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  SizedBox(height: isMobile ? 12 : 16),
                  CustomDivider(),
                  isLoading?Center(child: 
                  Padding(
                    padding:   EdgeInsets.all( 40),
                    child:LoadingMainCard())
                  ):SearchResultsItem(
                      data: ("Search Results", _mapSearchResults()),
                    ),
                  
                  const SizedBox(height: 16),
                  CustomDivider(),
                  SizedBox(height: isMobile ? 12 : 16),
                  // SearchStockItem(data: recentlyViewed),
                  SearchResultsItem(
                            data: (
                              "Recently Viewed",
                              ref.watch(recentlyVisitedProvider).map(
                                (stock) => (
                                  stock.imageUrl,
                                  stock.companyName,
                                  stock.symbol,
                                  stock.expiry,
                                  stock.id
                                )
                              ).toList()
                            ),
                  ),
                  SizedBox(height: isMobile ? 18 : 24),
                  isMostViewedLoading
                  ? Padding(
                      padding: const EdgeInsets.all(40),
                      child: LoadingMainCard(),
                    )
                  : SearchResultsItem(
                      data: ("Most viewed this week", _mapMostViewedResults()),
                    ),
                  SizedBox(height: isMobile ? 12 : 16),
                  CustomDivider(),
                  SizedBox(height: isMobile ? 6 : 8),
               
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class SearchStockItem extends ConsumerWidget {
  const SearchStockItem({super.key, required this.data});
  final (String header, List<(String, String, String)> values) data;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            data.$1,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w400,
              color: colors.always8B949E,
            ),
          ),
          const SizedBox(height: 32),
          for (var v in data.$2) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Image.asset(
                        v.$1,
                        fit: BoxFit.cover,
                        width: 40,
                        height: 40,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              v.$2,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                                letterSpacing: 0,
                                color: colors.alwaysWhite,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              v.$3,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w500,
                                letterSpacing: 0,
                                color: colors.always8B949E,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.arrow_forward,
                  color: colors.always8B949E,
                  size: 18,
                )
              ],
            ),
            const SizedBox(height: 24),
          ],
        ],
      ),
    );
  }
}


class SearchResultsItem extends ConsumerWidget {
  const SearchResultsItem({
    super.key,
    required this.data,
  });

  /// Format: ("Header", [("imageUrl", "Company Name", "Symbol", "Expiry")])
  // final (String header, List<(String, String, String, String)> values) data;
  final (String header, List<(String, String, String, String, int)> values) data;

  void _openStockProfile(BuildContext context, int marketId) {
    final router = GoRouter.of(context);
    final currentUri = router.routeInformationProvider.value.uri;
    final competitionId = currentUri.queryParameters['competitionId'];
    final route = competitionId == null || competitionId.isEmpty
        ? '/dashboard/stock-profile?id=$marketId'
        : '/dashboard/stock-profile?id=$marketId&competitionId=$competitionId';

    Navigator.of(context, rootNavigator: true).pop();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      router.go(route);
    });
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            data.$1,
            textAlign: TextAlign.left,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w400,
              color: colors.always8B949E,
            ),
          ),
          const SizedBox(height: 32),
          for (var v in data.$2) ...[
            Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () => _openStockProfile(context, v.$5),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Row(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.network(
                                v.$1,
                                width: 40,
                                height: 40,
                                fit: BoxFit.cover,
                                errorBuilder: (context, _, __) =>
                                    const Icon(Icons.image_not_supported),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text(
                                    v.$2,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w500,
                                      color: colors.alwaysWhite,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    "\$" + v.$3,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontSize: 15,
                                      fontWeight: FontWeight.w500,
                                      color: colors.always8B949E,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      Icon(
                        Icons.arrow_forward,
                        color: colors.always8B949E,
                        size: 18,
                      )
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ],
      ),
    );
  }
}
