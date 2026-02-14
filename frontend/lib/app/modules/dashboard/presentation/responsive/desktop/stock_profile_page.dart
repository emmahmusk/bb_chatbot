import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:frontend/app/shared/presentation/widgets/loading_main_card.dart';
import '../../providers/stock_selection_provider.dart'; 

import '../../../data/models/user_stock_selection_model.dart';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/providers/recently_visited_provider.dart';
import 'package:frontend/app/modules/dashboard/data/models/visited_stock_model.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:go_router/go_router.dart';


class StockProfilePage extends ConsumerStatefulWidget {
  final String id;
 
  const StockProfilePage({
    super.key,
    required this.id,
   });

  @override
  ConsumerState<StockProfilePage> createState() => _StockProfilePageState();
}

class _StockProfilePageState extends ConsumerState<StockProfilePage> {
  var market = {};
  bool isLoading = true;
  String htmlContent = '';
  late InAppWebViewController webViewController;
  String preferredOdds = 'D'; // Default
  bool isOddsLoaded = false;

  List<String>? expiryDates;
  String? selectedExpiry;

   double? selectedStrike;
final ScrollController _scrollController = ScrollController();


  @override
  void initState() {
    super.initState();
    loadPreferredOddsType();
    fetchMarkets();
  }


bool _isLoadingDialogOpen = false;
 
void showBullBearLoadingDialog(BuildContext context, {String? message}) {
  if (_isLoadingDialogOpen) return; // prevent duplicates

  _isLoadingDialogOpen = true;

  final screenWidth = MediaQuery.of(context).size.width;

  showDialog(
    context: context,
    useRootNavigator: true,
    barrierDismissible: false,
    barrierColor: Colors.black.withOpacity(0.4),
    builder: (ctx) {
      return Dialog(
        backgroundColor: const Color(0xFF1F242C),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: screenWidth * 0.5),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const LoadingMainCard(),
                if (message != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    message,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 14,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    },
  );
}



void hideBullBearDialog(BuildContext context) {
  if (_isLoadingDialogOpen) {
    Navigator.of(context, rootNavigator: true).pop();
    _isLoadingDialogOpen = false;
  }
}
  Future<void> loadPreferredOddsType() async {
  final prefs = await SharedPreferences.getInstance();
  final saved = prefs.getString('odds_type');
  if (saved != null && ['A', 'D', 'F'].contains(saved)) {
    setState(() {
      preferredOdds = saved;
      isOddsLoaded = true;
    });
  } else {
    setState(() {
      isOddsLoaded = true;
    });
  }
}

bool checkMarketOpenOrAlert(BuildContext context) {
  // final now = DateTime.now().toUtc();
  // final eastern = now.subtract(const Duration(hours: 4)); // EDT = UTC-4

  // final isWeekday = eastern.weekday >= 1 && eastern.weekday <= 5;
  // final isOpenHours = (eastern.hour > 9 || (eastern.hour == 9 && eastern.minute >= 30)) && eastern.hour < 16;

  // final isOpen = isWeekday && isOpenHours;

  // if (!isOpen) {
  //   ScaffoldMessenger.of(context).showSnackBar(
  //           const SnackBar(
  //             content: Text("Market is Currently Closed"),
  //             backgroundColor: Colors.redAccent,
  //             behavior: SnackBarBehavior.floating,
  //             duration: Duration(seconds: 3),
  //           ),
  //         );
  // }

  return true;
}
 Future<void> fetchExpiryDates(String symbol) async {
  showBullBearLoadingDialog(context, message: "Fetching expiry dates...");
  
  try {
    final res = await http.get(Uri.parse('https://api.bbbprediction.com/bet/expiries/?symbol=$symbol'));
    final decoded = json.decode(res.body);

    setState(() {
      expiryDates = List<String>.from(decoded['expiries']);
    });
  } catch (e) {
    print("Error fetching expiry dates: $e");
  } finally {
    hideBullBearDialog(context); // Will only pop if dialog was open
  }
}



String formatExpiryDate(String input) {
  // Input includes day of week, so keep 'EEE' in the parser
  final inputFormat = DateFormat('EEE, dd MMM yyyy');
  
  // Output as "Sep 19, 2025"
  final outputFormat = DateFormat('MMM d, yyyy');
  
  final date = inputFormat.parse(input);
  return outputFormat.format(date);
}


String formatToMMDDYYYY(String input) {
  final date = DateFormat('yyyy-MM-dd').parse(input);
  return DateFormat('MMM d, yyyy').format(date);
}

Future<void> _openExpiryDialog(String symbol) async {
  // fetch the dates first
  await fetchExpiryDates(symbol);
  if (!mounted || expiryDates == null || expiryDates!.isEmpty) return;

  String? localSelected = selectedExpiry;

  await showDialog<void>(
    context: context,
    barrierDismissible: true,
    builder: (ctx) {
      return Dialog(
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        backgroundColor: const Color(0xFF1F242C),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Theme(
          data: Theme.of(ctx).copyWith(
            unselectedWidgetColor: Colors.white,
            radioTheme: const RadioThemeData(
              fillColor: MaterialStatePropertyAll(Colors.white),
            ),
          ),
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: 500, // ⬅️ Decreased from 700
              maxHeight: 500,
            ),
            child: Stack(
              children: [
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: StatefulBuilder(
                    builder: (ctx, setLocal) {
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Select Expiry Date',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 12),
                          const Divider(color: Colors.white24, height: 1),
                          const SizedBox(height: 8),
                          Expanded(
                            child: ScrollbarTheme(
                              data: ScrollbarThemeData(
                                thumbColor: MaterialStateProperty.all(Colors.white),
                                trackColor: MaterialStateProperty.all(Colors.white24),
                                thickness: MaterialStateProperty.all(6),
                                radius: const Radius.circular(10),
                              ),
                              child: Scrollbar(
                                thumbVisibility: true,
                                child: ListView(
                                  children: expiryDates!
                                      .map((e) => RadioListTile<String>(
                                            value: e,
                                            groupValue: localSelected,
                                            activeColor: Colors.white,
                                            title: Text(
                                              formatToMMDDYYYY(e),
                                              style: const TextStyle(
                                                fontSize: 14,
                                                fontWeight: FontWeight.w500,
                                                color: Colors.white,
                                              ),
                                            ),
                                            onChanged: (val) async {
                                              if (val == null) return;
                                              setLocal(() => localSelected = val);
                                              setState(() => selectedExpiry = val);
                                              Navigator.of(ctx).pop();
                                              await _openStrikePriceDialog(symbol, val);
                                            },
                                          ))
                                      .toList(),
                                ),
                              ),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ),

                // Close button (top-right)
                Positioned(
                  top: 8,
                  right: 8,
                  child: GestureDetector(
                    onTap: () => Navigator.of(ctx).pop(),
                    child: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.close,
                        size: 20,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    },
  );
}



Future<void> handleOverUnderTap(String outcomeType) async {
  setState(() => isLoading = true);

   

  // ✅ Refresh latest market data from API
  final refreshed = await fetchMarkets();

   

  final selectedStocks = ref.read(selectedStockProvider);
  final alreadySelected = selectedStocks.any(
    (s) => s.marketId == market['id'] && s.chosenOutcome == outcomeType,
  );

  if (alreadySelected) {
    ref.read(selectedStockProvider.notifier).remove(market['id']);
  } else {
    final impliedOdds = outcomeType == "over"
        ? double.tryParse(market['implied_odds_over']?.toString() ?? '0')
        : double.tryParse(market['implied_odds_under']?.toString() ?? '0');

    final odds = outcomeType == "over"
        ? getOdds(
          
            market['odds_over'],
            impliedOdds: impliedOdds,
           
          )
        : getOdds(
             
            market['odds_under'],
            impliedOdds: impliedOdds,
            
          );

    if (odds == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Odds not available for this market."),
          backgroundColor: Colors.redAccent,
          behavior: SnackBarBehavior.floating,
        ),
      );
      setState(() => isLoading = false);
      return;
    }

    final stock = SelectedStockModel(
      marketId: market['id'],
      marketName: market['stock']['company_name'] ?? market['stock']['symbol'],
      chosenOutcome: outcomeType,
      odds: odds,
      companyName: market['stock']['company_name'] ?? '',
      companySymbol: market['stock']['symbol'],
      logoUrl: market['stock']['url'] ?? '',
      targetPrice: double.tryParse(market['target_price'].toString()) ?? 0.0,
      expiryDate: market['expiry_date'].toString(),
    );

    ref.read(selectedStockProvider.notifier).insertOrUpdate(stock);
  }

  setState(() => isLoading = false);
}



  Future<void> _openStrikePriceDialog(String symbol, String expiry) async {
  try {
    showBullBearLoadingDialog(context, message: "Fetching strike prices...");

    final res = await http.get(Uri.parse(
      'https://api.bbbprediction.com/bet/markets/?search=$symbol&expiry=$expiry',
    ));
    hideBullBearDialog(context);
    final decoded = json.decode(res.body);
    print(decoded);
    print("Strike Prices Chethan");
    List strikes = List.from(decoded['results']);
    strikes.sort((a, b) =>
      double.parse(a['target_price'].toString()).compareTo(
        double.parse(b['target_price'].toString())
      )
    );

    print("✅ Sorted Strike Prices (DESC):");
    for (var s in strikes) {
      print("Target: ${s['target_price']}, Expiry: ${s['expiry_date']}");
    }
    
    // Remove duplicates based on target_price
    final seenPrices = <double>{};
    strikes = strikes.where((item) {
      final price = double.parse(item['target_price'].toString());
      if (seenPrices.contains(price)) {
        return false;
      } else {
        seenPrices.add(price);
        return true;
      }
    }).toList();

    // Print to confirm
    print("✅ Sorted & Unique Strike Prices:");
    for (var s in strikes) {
      print("Target: ${s['target_price']}, Expiry: ${s['expiry_date']}");
    }
    

    double? localSelectedStrike = selectedStrike;
    final prefs = await SharedPreferences.getInstance();
  final saved = prefs.getString('odds_type');
  
    await showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) {
        return Dialog(
          insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
          backgroundColor: const Color(0xFF1F242C),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Theme(
            data: Theme.of(ctx).copyWith(
              unselectedWidgetColor: Colors.white,
              radioTheme: const RadioThemeData(
                fillColor: MaterialStatePropertyAll(Colors.white),
              ),
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 500, maxHeight: 500),
              child: Stack(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: StatefulBuilder(
                      builder: (ctx, setLocal) {
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Select Strike Price',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                            const SizedBox(height: 12),
                            const Divider(color: Colors.white24, height: 1),
                            const SizedBox(height: 8),
                            Row(
                                          mainAxisSize: MainAxisSize.max,
                                          // mainAxisAlignment: MainAxisAlignment.end,
                                          children: [
                                            SizedBox(width: 20.0,),
                                            Container(
                                                  margin:EdgeInsets.all(10.0),
                                                              width: 100,
                                                              padding: const EdgeInsets.symmetric(vertical: 6),
                                                              decoration:   BoxDecoration(
                                                                color: Colors.white, 
                                                                 border: Border.all(
                                                                    color: Colors.white,  
                                                                    width: 1.5,           
                                                                  ),
                                                                borderRadius: BorderRadius.all(
                                                                  Radius.circular(8) 
                                                                ),
                                                              ),
                                                              child:   Center(
                                                                child: Text(
                                                                  "Strike Price ",
                                                                  style: TextStyle(
                                                                    color:  Color(0xFF1F242C),
                                                                    fontSize: 12, 
                                                                    fontWeight: FontWeight.bold,
                                                                  ),
                                                                ),
                                                              ),
                                            ),       
                                            SizedBox(width: 62.0,),
                                            Row(
                                              children: [
                                                 
                                                  Container(
                                                    margin:EdgeInsets.all(10.0),
                                                          width: 100,
                                                          padding: const EdgeInsets.symmetric(vertical: 6),
                                                          decoration:   BoxDecoration(
                                                            color: Colors.white, 
                                                            borderRadius: BorderRadius.all(
                                                              Radius.circular(8) 
                                                            ),
                                                            border: Border.all(
                                                                    color: Colors.white,  
                                                                    width: 1.5,           
                                                                  ),
                                                          ),
                                                          child:   Center(
                                                            child: Text(
                                                              "Over ",
                                                              style: TextStyle(
                                                                color:   Color(0xFF1F242C),
                                                                fontSize: 12, 
                                                                fontWeight: FontWeight.bold,
                                                              ),
                                                            ),
                                                          ),
                                                        ),
                                                        Container(
                                                  margin:EdgeInsets.all(10.0),
                                                              width: 100,
                                                              padding: const EdgeInsets.symmetric(vertical: 6),
                                                              decoration:   BoxDecoration(
                                                                color: Colors.white, 
                                                                 border: Border.all(
                                                                    color: Colors.white,  
                                                                    width: 1.5,           
                                                                  ),
                                                                borderRadius: BorderRadius.all(
                                                                  Radius.circular(8) 
                                                                ),
                                                              ),
                                                              child:   Center(
                                                                child: Text(
                                                                  "Under ",
                                                                  style: TextStyle(
                                                                    color:  Color(0xFF1F242C),
                                                                    fontSize: 12, 
                                                                    fontWeight: FontWeight.bold,
                                                                  ),
                                                                ),
                                                              ),
                                                            ),
                                              ],
                                            ),
                                            SizedBox(width: 25.0,)
                                          ],
                                        ),
                            Expanded(
                              child: ScrollbarTheme(
                                data: ScrollbarThemeData(
                                  thumbColor: MaterialStateProperty.all(Colors.white),
                                  trackColor: MaterialStateProperty.all(Colors.white24),
                                  thickness: MaterialStateProperty.all(6),
                                  radius: const Radius.circular(10),
                                ),
                                child: Scrollbar(
                                  thumbVisibility: true,
                                  child: ListView(
                                    children: strikes.map((sp) {
                                      final double targetPrice = double.tryParse(sp['target_price'].toString()) ?? 0.0;
                                      
                                      // Extract implied odds
                                      final impliedOddsOver = double.tryParse(sp['implied_odds_over']?.toString() ?? '0') ?? 0.0;
                                      final impliedOddsUnder = double.tryParse(sp['implied_odds_under']?.toString() ?? '0') ?? 0.0;
                                      
                                      // Get formatted odds based on preference
                                      var odds_over;
                                      var odds_under;
                                      
                                      if(saved=='A'){
                                            odds_over=sp['odds_over']['american'];
                                            odds_under=sp['odds_under']['american'];
                                        }else if(saved =='D'){
                                            odds_over=sp['odds_over']['decimal'];
                                            odds_under=sp['odds_under']['decimal'];
                                        }else if(saved =='F'){
                                          odds_over=sp['odds_over']['fractional'];
                                            odds_under=sp['odds_under']['fractional'];
                                        }else if(saved =='P'){
                                          // Calculate probability percentage
                                          odds_over = impliedOddsOver > 0 ? '${(impliedOddsOver * 100).toStringAsFixed(2)}%' : 'N/A';
                                          odds_under = impliedOddsUnder > 0 ? '${(impliedOddsUnder * 100).toStringAsFixed(2)}%' : 'N/A';
                                        }else{
                                          odds_over=sp['odds_over']['decimal'];
                                          odds_under=sp['odds_under']['decimal'];
                                        }
                                      
                                      return RadioListTile<double>(
                                        value: targetPrice,
                                        groupValue: localSelectedStrike,
                                        activeColor: Colors.white,
                                        title: Row(
                                          mainAxisSize: MainAxisSize.max,
                                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                          children: [
                                            Text(
                                             "\$"+targetPrice.toStringAsFixed(2),
                                              style: const TextStyle(
                                                fontSize: 14,
                                                fontWeight: FontWeight.w500,
                                                color: Colors.white,
                                              ),
                                            ),
                                            Row(
                                              children: [
                                                  
                                                  Container(
                                                    margin:EdgeInsets.all(10.0),
                                                          width: 100,
                                                          padding: const EdgeInsets.symmetric(vertical: 6),
                                                          decoration:   BoxDecoration(
                                                            color: Color(0xFF1F242C), 
                                                            borderRadius: BorderRadius.all(
                                                              Radius.circular(8) 
                                                            ),
                                                            border: Border.all(
                                                                    color: Colors.white,  
                                                                    width: 1.5,           
                                                                  ),
                                                          ),
                                                          child:   Center(
                                                            child: Text(
                                                              "$odds_over",
                                                              style: TextStyle(
                                                                color:   Colors.white,
                                                                fontSize: 12, 
                                                                fontWeight: FontWeight.w500,
                                                              ),
                                                            ),
                                                          ),
                                                        ),
                                                        Container(
                                                  margin:EdgeInsets.all(10.0),
                                                              width: 100,
                                                              padding: const EdgeInsets.symmetric(vertical: 6),
                                                              decoration:   BoxDecoration(
                                                                color: Color(0xFF1F242C), 
                                                                 border: Border.all(
                                                                    color: Colors.white,  
                                                                    width: 1.5,           
                                                                  ),
                                                                borderRadius: BorderRadius.all(
                                                                  Radius.circular(8) 
                                                                ),
                                                              ),
                                                              child:   Center(
                                                                child: Text(
                                                                  "$odds_under",
                                                                  style: TextStyle(
                                                                    color:  Colors.white,
                                                                    fontSize: 12, 
                                                                    fontWeight: FontWeight.w500,
                                                                  ),
                                                                ),
                                                              ),
                                                            )
                                              ],
                                            ),
                                            
                                          ],
                                        ),
                                        onChanged: (val) async {
                                          if (val == null) return;
                                          setLocal(() => localSelectedStrike = val);
                                          setState(() => selectedStrike = val);
                                          Navigator.of(ctx).pop();
                                          await fetchUpdatedMarket(symbol, expiry, val);
                                        },
                                      );
                                    }).toList(),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                  ),
                  Positioned(
                    top: 8,
                    right: 8,
                    child: GestureDetector(
                      onTap: () => Navigator.of(ctx).pop(),
                      child: Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.1),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.close,
                          size: 20,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  } catch (e) {
    // Handle errors if needed
  } finally {
    
  }
}


String getOdds(Map<String, dynamic> oddsData, {double? impliedOdds}) {
  switch (preferredOdds) {
    case 'A':
      return oddsData['american']?.toString() ?? 'N/A';
    case 'F':
      return oddsData['fractional']?.toString() ?? 'N/A';
    case 'P':
      // Convert implied probability to percentage and format
      if (impliedOdds != null && impliedOdds > 0) {
        final probability = impliedOdds * 100;
        return '${probability.toStringAsFixed(2)}%';
      }
      return 'N/A';
    case 'D':
    default:
      return oddsData['decimal']?.toString() ?? 'N/A';
  }
}


  @override
  void didUpdateWidget(covariant StockProfilePage oldWidget) {
    super.didUpdateWidget(oldWidget);

    // if (oldWidget.symbol != widget.symbol || oldWidget.expiryDate != widget.expiryDate) {
      setState(() {
        isLoading = true;
        htmlContent = '';
      });
      fetchMarkets();
    // }
  }

  Future<void> fetchMarkets() async {
    try {
     

      final url = 'https://api.bbbprediction.com/bet/markets/${widget.id}/';
      
      final response = await http.get(Uri.parse(url));
       
      if (response.statusCode == 200) {
        var  data = json.decode(response.body);
        final marketData = data  ;

          print("Single Market Data Chethan: ");
          print(marketData);
         
        
        final html = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
    <style>
  html, body {
    margin: 0;
    padding: 0;
    background-color: transparent;
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  

   .tradingview-widget-container {
    width: 100vw;
    height: 100%;
  }

  .tradingview-widget-container__widget {
    width: 100%;
    height: 400px;
  }
   </style>
</head>
<body>
  <div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
    {
      "symbols": [["${marketData['stock']['symbol']}", "${marketData['stock']['symbol']}|1D"]],
      "chartType": "area",
      "colorTheme": "dark",
      "backgroundColor": "transparent",
      "isTransparent": true,
      "autosize": true,
      "locale": "en"
    }
    </script>
  </div>
</body>
</html>
''';



        setState(() {
          market = marketData;
          htmlContent = html;
          isLoading = false;
        });
         final recentlyVisited = VisitedStockModel(
            imageUrl: marketData['stock']['url'] ?? '',
            companyName: marketData['stock']['company_name'] ?? '',
            symbol: marketData['stock']['symbol'] ?? '',
            expiry: marketData['expiry_date'] ?? '',
            id: marketData['id'] as int,
          );

          // Read the current list from the provider
          final currentList = ref.read(recentlyVisitedProvider);

          // Check if the item with same ID already exists
          final alreadyExists = currentList.any((item) => item.id == recentlyVisited.id);

          // If not present, add it
          if (!alreadyExists) {
            ref.read(recentlyVisitedProvider.notifier).add(recentlyVisited);
}

      } else {
         setState(() => isLoading = false);
      }
    } catch (e) {
       setState(() => isLoading = false);
    }
  }


  Future<void> fetchUpdatedMarket(String symbol, String expiry, double strike) async {
     
  final url = 'https://api.bbbprediction.com/bet/markets/?search=$symbol&expiry=$expiry&strike=${strike.toStringAsFixed(2)}';
  try {
    final res = await http.get(Uri.parse(url));
    if (res.statusCode == 200) {
      final data = json.decode(res.body);
      print("Fetched Market : $symbol - $expiry - $strike");
      print(data );
      if (data['results'] != null && data['results'].isNotEmpty) {
        // setState(() {
        //   market = data['results'][0];
        //   selectedExpiry = expiry;
        //   selectedStrike = strike;
        // });
        var id =data['results'][0]['id'];
        context.go('/dashboard/stock-profile?id=$id');
      } else{
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text("No market data found for the selected expiry and strike price."),
              backgroundColor: Colors.redAccent,
              behavior: SnackBarBehavior.floating,
              duration: Duration(seconds: 3),
            ),
          );
        }
      }
    }
  } catch (e) {
   }
}

Future<void> _showFullScreenGraph() async {
  await showDialog(
    context: context,
    barrierDismissible: true,
    builder: (ctx) {
      final size = MediaQuery.of(ctx).size;
      return Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: EdgeInsets.zero,
        child: StatefulBuilder(
          builder: (ctx, setLocal) {
            bool isLoading = true;

            return Stack(
              children: [
                // WebView background container
                Container(
                  width: size.width,
                  height: size.height,
                  color: const Color(0xFF1F242C),
                  padding: const EdgeInsets.only(top: 60, left: 12, right: 12, bottom: 12),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Stack(
                      children: [
                        InAppWebView(
                          initialData: InAppWebViewInitialData(data: htmlContent),
                          onLoadStop: (_, __) {
                            setLocal(() => isLoading = false);
                          },
                        ),
                        if (isLoading)
                          const Center(
                            child: CircularProgressIndicator(color: Colors.white),
                          ),
                      ],
                    ),
                  ),
                ),

                // Close button
                Positioned(
                  top: 20,
                  right: 20,
                  child: GestureDetector(
                    onTap: () => Navigator.of(ctx).pop(),
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.6),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.close, color: Colors.white, size: 24),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      );
    },
  );
}



  @override
  Widget build(BuildContext context) {
       final covered = !(ModalRoute.of(context)?.isCurrent ?? true);

    return Padding(
     padding: const EdgeInsets.only(left: 40),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: Color(0xFF1F242C)),
          borderRadius: BorderRadius.circular(12),
        ),
        child: isLoading?  Center(child: LoadingMainCard()):ScrollbarTheme(
          data: ScrollbarThemeData(
              thumbColor: WidgetStateProperty.all(Colors.white54),
              thickness: WidgetStateProperty.all(6),
              radius: const Radius.circular(10),
              trackVisibility: WidgetStateProperty.all(true),
            ),
          child: Scrollbar(
            controller: _scrollController,
            thumbVisibility: true,
            thickness: 6,
            radius: const Radius.circular(8),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Column(
                  mainAxisAlignment: MainAxisAlignment.start,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Container(
                      margin: const EdgeInsets.only(bottom: 12),
                                          padding: const EdgeInsets.only(  top:16),
                                          decoration: BoxDecoration(
                                            // border: Border.all(color:  Color(0xFF1F242C)),
                                            // borderRadius: BorderRadius.circular(10),
                                          ),
                                          child: Column(
                                            children: [
                                                
                                                   Row(
                                                     mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                                    crossAxisAlignment: CrossAxisAlignment.start,
                                                     children: [
                                                      // LEFT SIDE
                                                       Padding(
                                                         padding: const EdgeInsets.only(left:16.0),
                                                         child: Column(
                                                            crossAxisAlignment: CrossAxisAlignment.start,
                                                            children: [
                                                              Row(
                                                                children: [
                                                               GestureDetector(
                                                                      onTap: () {
                                                                        // final symbol = market['stock']['symbol'];
                                                                        // final expiry = market['expiryDate']; // Make sure it's a valid string (e.g., "2025-08-13")
                                                                        // context.go('/dashboard/stock-profile?symbol=$symbol&expiry=$expiry');
                                                                      },
                                                                      child:  (market['stock']['url'] != null)?
                                                            ClipRRect(
                                                                borderRadius: BorderRadius.circular(6), // adjust for roundness
                                                                child: Image.network(
                                                                  market['stock']['url'],
                                                                  width: 32,
                                                                  height: 32,
                                                                  fit: BoxFit.cover,
                                                                ),
                                                              )
                                                            : Container(
                                                                width: 32,
                                                                height: 32,
                                                                decoration: BoxDecoration(
                                                                  color: Colors.white,
                                                                  borderRadius: BorderRadius.circular(6),
                                                                ),
                                                                alignment: Alignment.center,
                                                                child: Text(
                                                                  (market['stock']['symbol'].length >= 2
                                                                      ? market['stock']['symbol'].substring(0, 2)
                                                                      : market['stock']['symbol'])
                                                                      .toUpperCase(),
                                                                  style: const TextStyle(
                                                                    fontSize: 14,
                                                                    fontWeight: FontWeight.bold,
                                                                    color: Colors.black,
                                                                  ),
                                                                ),
                                                              )
                                                          ,
                                                                    ),
                                                                                               
                                                                  const SizedBox(width: 10),
                                                                 Column(
                                                                  crossAxisAlignment: CrossAxisAlignment.start,
                                                                  children: [
                                                                    /// Row for company name and symbol
                                                                    Row(
                                                                      crossAxisAlignment: CrossAxisAlignment.center,
                                                                      children: [
                                                                        if (market['stock']['company_name'] != null)
                                                                          Text(
                                                                            "${market['stock']['company_name']!} - ",
                                                                            style: const TextStyle(
                                                                              fontSize: 14,
                                                                              color: Colors.white,
                                                                              fontWeight: FontWeight.w500,
                                                                            ),
                                                                          ),
                                                                        Text(
                                                                          "\$"+market['stock']['symbol'].toString(),
                                                                          style: const TextStyle(
                                                                            fontSize: 14,
                                                                            color: Color(0xFF888888), // dark gray
                                                                            fontWeight: FontWeight.w500,
                                                                          ),
                                                                        ),
                                                                      ],
                                                                    ),
                                                                                               
                                                                    const SizedBox(height: 4), // spacing between rows
                                                                                               
                                                                    /// Strike price on a new line
                                                                    Text(
                                                                      "\$${market['target_price']}",
                                                                      style: const TextStyle(
                                                                        fontSize: 16, // slightly larger
                                                                        fontWeight: FontWeight.w600, // semi-bold
                                                                        color: Colors.white,
                                                                      ),
                                                                    ),
                                                                  ],
                                                                )
                                                                                               
                                                                                               
                                                                ],
                                                              ),
                                                           
                                                              const SizedBox(height: 10),
                                                              
                                                              
                                                                               
                                                                                
                                                            ],
                                                          ),
                                                       ),
            
                                                       Padding(
              padding: const EdgeInsets.only(right: 16.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  /// OVER BLOCK
                  Builder(builder: (context) {
            final selectedStocks = ref.watch(selectedStockProvider);
            final isOverSelected = selectedStocks.any((s) => s.marketId == market['id'] && s.chosenOutcome == "over");
            
            return Column(
              children: [
                // Top Label Box
                Container(
                  width: 100,
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  decoration: BoxDecoration(
                    color: isOverSelected ? Colors.white : const Color(0xFF1F242C),
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(8),
                      topRight: Radius.circular(8),
                    ),
                  ),
                  child: Center(
                    child: Text(
                      "Over",
                      style: TextStyle(
                        color: isOverSelected ? const Color(0xFF1F242C) : const Color(0xFFD3D3D3),
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                // Bottom Value Box
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () async{
                      
                      if (!checkMarketOpenOrAlert(context)) return;
                      //  await handleOverUnderTap("over");
                      final alreadySelected = selectedStocks.any(
                        (s) => s.marketId == market['id'] && s.chosenOutcome == "over",
                      );
                              
                      if (alreadySelected) {
                        ref.read(selectedStockProvider.notifier).remove(market['id']);
                      } else {
                        setState(() {
                          isLoading=true;
                        });
                        await fetchMarkets();
                  
                        final stock = SelectedStockModel(
                          marketId: market['id'],
                          marketName: market['stock']['company_name'] ?? market['stock']['symbol'],
                          chosenOutcome: "over",
                          odds: market['odds_over']['decimal'] ?? 'N/A',
                          companyName: market['stock']['company_name'] ?? '',
                          companySymbol: market['stock']['symbol'],
                          logoUrl: market['stock']['url'] ?? '',
                          targetPrice: double.tryParse(market['target_price'].toString()) ?? 0.0,
                          expiryDate: market['expiry_date'].toString(),
                        );
                        ref.read(selectedStockProvider.notifier).insertOrUpdate(stock);
                      }
                    },
                    child: Container(
                      width: 100,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      decoration: BoxDecoration(
                        color: isOverSelected ? Colors.white : const Color(0xFF1F242C),
                        borderRadius: const BorderRadius.only(
                          bottomLeft: Radius.circular(8),
                          bottomRight: Radius.circular(8),
                        ),
                      ),
                      child: Center(
                        child: Text(
                         getOdds(
                           market['odds_over'],
                           impliedOdds: double.tryParse(market['implied_odds_over']?.toString() ?? '0'),
                         ),
                          style: TextStyle(
                            color: isOverSelected ? const Color(0xFF1F242C) : Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            );
                  }),
            
                  const SizedBox(width: 12),
            
                  /// UNDER BLOCK
                  Builder(builder: (context) {
            final selectedStocks = ref.watch(selectedStockProvider);
            final isUnderSelected = selectedStocks.any((s) => s.marketId == market['id'] && s.chosenOutcome == "under");
            
            return Column(
              children: [
                Container(
                  width: 100,
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  decoration: BoxDecoration(
                    color: isUnderSelected ? Colors.white : const Color(0xFF1F242C),
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(8),
                      topRight: Radius.circular(8),
                    ),
                  ),
                  child: Center(
                    child: Text(
                      "Under",
                      style: TextStyle(
                        color: isUnderSelected ? const Color(0xFF1F242C) : const Color(0xFFD3D3D3),
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () async{
                      
                      if (!checkMarketOpenOrAlert(context)) return;
                      //  await handleOverUnderTap("under");
                      final alreadySelected = selectedStocks.any(
                        (s) => s.marketId == market['id'] && s.chosenOutcome == "under",
                      );
                              
                      if (alreadySelected) {
                        ref.read(selectedStockProvider.notifier).remove(market['id']);
                      } else {
                        setState(() {
                            isLoading=true;
                        });
                        await fetchMarkets();
                        final stock = SelectedStockModel(
                          marketId: market['id'],
                          marketName: market['stock']['company_name'] ?? market['stock']['symbol'],
                          chosenOutcome: "under",
                          odds: market['odds_under']['decimal'] ?? 'N/A',
                          companyName: market['stock']['company_name'] ?? '',
                          companySymbol: market['stock']['symbol'],
                          logoUrl: market['stock']['url'] ?? '',
                          targetPrice: double.tryParse(market['target_price'].toString()) ?? 0.0,
                          expiryDate: market['expiry_date'].toString(),
                        );
                        ref.read(selectedStockProvider.notifier).insertOrUpdate(stock);
                      }
                    },
                    child: Container(
                      width: 100,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      decoration: BoxDecoration(
                        color: isUnderSelected ? Colors.white : const Color(0xFF1F242C),
                        borderRadius: const BorderRadius.only(
                          bottomLeft: Radius.circular(8),
                          bottomRight: Radius.circular(8),
                        ),
                      ),
                      child: Center(
                        child: Text(
                          getOdds(
                            market['odds_under'],
                            impliedOdds: double.tryParse(market['implied_odds_under']?.toString() ?? '0'),
                          ),
                          style: TextStyle(
                            color: isUnderSelected ? const Color(0xFF1F242C) : Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            );
                  }),
                ],
              ),
            )
            
                                                     ],
                                                   ),
            
                                                    
            
            
                                            ],
                                          ),
                    ),
            
                                           Container(
                                                padding:   EdgeInsets.only(left:20, right: 40, top: 15.0, bottom: 15.0),
                                                margin: const EdgeInsets.only(top: 8),
                                                 
                                                child:  Row(
                                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                                    children: [
                                                      /// Expiry Left
                                                      GestureDetector(
                                                onTap: () async {
                                                  await _openExpiryDialog(market['stock']['symbol'].toString());
                                                },
                                                child: MouseRegion(
                                                      cursor: SystemMouseCursors.click,
                                                      child: RichText(
                                                        text: TextSpan(
                                                          children: [
                                                            WidgetSpan(
                                                              alignment: PlaceholderAlignment.middle,
                                                              child: Padding(
                                                                padding: const EdgeInsets.only(right: 6),
                                                                child: Icon(
                                                                  Icons.edit,
                                                                  size: 14,
                                                                  color: Colors.white,
                                                                ),
                                                              ),
                                                            ),
                                                            const TextSpan(
                                                              text: "Exp: ",
                                                              style: TextStyle(
                                                                fontSize: 14,
                                                                fontWeight: FontWeight.w500,
                                                                color: Color(0xFF888888),
                                                              ),
                                                            ),
                                                            TextSpan(
                                                              text: formatExpiryDate(market['expiry_date']),
                                                              style: const TextStyle(
                                                                fontSize: 14,
                                                                fontWeight: FontWeight.w600,
                                                                color: Colors.white,
                                                              ),
                                                            ),
                                                          ],
                                                        ),
                                                      ),
                                                    ), 
                                              ),
                                                      
                                                      
                                                                           
                                                  MouseRegion(
                                                    cursor: SystemMouseCursors.click,
                                                    child: GestureDetector(
                                                    onTap: ()async{
                                                        
                                                        // Parse the original date string
                                                            final inputFormat = DateFormat('EEE, dd MMM yyyy');
                                                            final outputFormat = DateFormat('yyyy-MM-dd');

                                                            try {
                                                              final parsedDate = inputFormat.parse(market['expiry_date']);
                                                              final formattedExpiry = outputFormat.format(parsedDate);

                                                              await _openStrikePriceDialog(market['stock']['symbol'], formattedExpiry);
                                                            } catch (e) {
                                                              print("Date parsing failed: $e");
                                                            }
                                                      },
                                                      
                                                      child: Container(
                                                        padding: EdgeInsets.all(10.0),
                                                        decoration: BoxDecoration(
                                                          color:  Color(0xFF1F242C),
                                                          borderRadius: BorderRadius.circular(20), // or any radius you prefer
                                                          border: Border.all(
                                                            color: Color(0xFFB0B0B0), // dark grey border
                                                            width: 1, // optional: thickness of the border
                                                          ),
                                                                  
                                                        ),
                                                        child: Row(
                                                          crossAxisAlignment: CrossAxisAlignment.center,
                                                          children: [
                                                            Image.asset(
                                                              'assets/media/pngs/strike_price.png',
                                                              width: 18,
                                                              height: 18,
                                                              fit: BoxFit.contain,
                                                            ),
                                                            const SizedBox(width: 6),
                                                            RichText(
                                                              text: TextSpan(
                                                                children: [
                                                                  const TextSpan(
                                                                    text: "Strike Price: ",
                                                                    style: TextStyle(
                                                                      fontSize: 14,
                                                                      fontWeight: FontWeight.w500,
                                                                      color: Colors.white,
                                                                    ),
                                                                  ),
                                                                  TextSpan(
                                                                    text: "\$${market['target_price']}",
                                                                    style: const TextStyle(
                                                                      fontSize: 14,
                                                                      fontWeight: FontWeight.w500,
                                                                      color: Colors.white,
                                                                    ),
                                                                  ),
                                                                ],
                                                              ),
                                                            ),
                                                          ],
                                                        ),
                                                      ),
                                                    ),
                                                  )
                                                                                        ],
                                                                                      ),
                                                ),
                    
                      
                   
            
                    const SizedBox(height: 20),
                    // SizedBox(
                    //     height: 400, // match the CSS above
                    //     width: double.infinity,
                    //     child: Offstage(
                    //       offstage: covered,
                    //       child: InAppWebView(
                    //         initialData: InAppWebViewInitialData(data: htmlContent),
                    //         onWebViewCreated: (controller) => webViewController = controller,
                    //       ),
                    //     ),
                    //   ),

//                       Align(
//   alignment: Alignment.centerRight,
//   child: TextButton.icon(
//     onPressed: _showFullScreenGraph,
//     icon: const Icon(Icons.fullscreen, color: Colors.white),
//     label: const Text(
//       "View Fullscreen",
//       style: TextStyle(color: Colors.white),
//     ),
//   ),
// ),

                  ],
                
                )
              
              ],
            ),
          ),
        ),
      ),
    );
  }
}
