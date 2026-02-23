import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// import 'package:frontend/app/modules/dashboard/presentation/providers/get_markets_provider.dart';
import 'package:frontend/app/modules/dashboard/presentation/widgets/trending/weekly_trending_bets.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/loadable_section.dart';

import 'package:intl/intl.dart';
import 'package:frontend/app/modules/dashboard/data/models/market_model_new.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/get_markets_provider_new.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';
import 'dart:developer';
import 'dart:convert'; 
import 'package:http/http.dart' as http;
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/app/shared/providers/preferences_provider.dart';

import '../../providers/stock_selection_provider.dart'; 

import '../../../data/models/user_stock_selection_model.dart';
import 'package:frontend/app/shared/presentation/widgets/loading_main_card.dart';

class DesktopTechStocksPage extends ConsumerStatefulWidget {
  const DesktopTechStocksPage({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _DesktopTechStocksPageState();
}

class _DesktopTechStocksPageState extends ConsumerState<DesktopTechStocksPage> {
  final ScrollController _scrollController = ScrollController();


   List<String>? expiryDates;
  String? selectedExpiry;

   double? selectedStrike;

String? currentPage='1';


bool _isLoadingDialogOpen = false;


final Map<int, GlobalKey> marketKeys = {};

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

int? updatingMarketId;

Future<void> fetchAndReplaceMarket(
  String symbol,
  String expiry,
  double strike,
  String chosenOutcome,
  int marketId,
) async {
  setState(() => updatingMarketId = marketId);

  try {
    // 🔄 Trigger re-fetch
    await ref.read(getMarketsProviderNew.notifier).get(queryParams: {
       
      'page': currentPage ?? '1',
    });

    final state = ref.read(getMarketsProviderNew);

    if (state is SuccessState) {
      final updatedMarket = state.data.results.firstWhere(
        (m) =>
            m.stock.symbol == symbol &&
            m.expiryDate == expiry &&
            m.targetPrice.toStringAsFixed(2) == strike.toStringAsFixed(2),
        orElse: () => MarketModel.empty(),
      );
      print("What is this null issue?");
      print(updatedMarket.id);
      print(updatedMarket.stock.companyName);
      print(updatedMarket.id.runtimeType);                  // prints the type of id (e.g., int)
      print(updatedMarket.stock.companyName.runtimeType);   // prints the type of companyName (e.g., String)
      if (updatedMarket.stock.companyName != null) {
        // 🎯 Get odds with implied probability
        final impliedOdds = chosenOutcome == "over"
            ? double.tryParse(updatedMarket.impliedOddsOver)
            : double.tryParse(updatedMarket.impliedOddsUnder);
        final odds = chosenOutcome == "over"
            ? getOdds(updatedMarket.oddsAOver, updatedMarket.oddsDOver, updatedMarket.oddsFOver, impliedOdds: impliedOdds)
            : getOdds(updatedMarket.oddsAUnder, updatedMarket.oddsDUnder, updatedMarket.oddsFUnder, impliedOdds: impliedOdds);

        // ❌ If odds are null, exit
        if (odds == null) {
          print("❌ Odds are null for market ID ${updatedMarket.id}. Skipping.");
          return;
        }

        // ✅ Build selected stock object
        final stock = SelectedStockModel(
          marketId: updatedMarket.id,
          marketName: updatedMarket.stock.companyName ?? updatedMarket.stock.symbol,
          chosenOutcome: chosenOutcome,
          odds: odds,
          companyName: updatedMarket.stock.companyName ?? '',
          companySymbol: updatedMarket.stock.symbol,
          logoUrl: updatedMarket.stock.logoUrl ?? '',
          targetPrice: updatedMarket.targetPrice,
          expiryDate: updatedMarket.expiryDate,
          decimalOdds: chosenOutcome == "over"
              ? updatedMarket.oddsDOver
              : updatedMarket.oddsDUnder,
        );

        ref.read(selectedStockProvider.notifier).insertOrUpdate(stock);
        print("✅ Stock inserted/updated for market ID: ${updatedMarket.id}");

        // 🔽 Scroll to selected market after UI rebuild
        WidgetsBinding.instance.addPostFrameCallback((_) async {
          await Future.delayed(const Duration(milliseconds: 300));

          final key = marketKeys[updatedMarket.id!];
          if (key != null && key.currentContext != null) {
            print("🟢 Scrolling to market ID: ${updatedMarket.id}");
            Scrollable.ensureVisible(
              key.currentContext!,
              duration: const Duration(milliseconds: 500),
              alignment: 0.1,
              curve: Curves.easeInOut,
            );
          } else {
            print("⚠️ Could not scroll to market: key/context missing.");
          }
        });

      } else {
        print("❌ No matching market found for symbol $symbol - $expiry - $strike");
      }
    }
  } catch (e) {
    print("❌ Error in fetchAndReplaceMarket: $e");
  } finally {
    setState(() => updatingMarketId = null);
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


Future<void> fetchUpdatedMarket(String symbol, String expiry, double strike) async {
  print("$symbol - $expiry - $strike");

  final url = 'https://api.bbbprediction.com/bet/markets/?search=$symbol&expiry=$expiry&strike=${strike.toStringAsFixed(2)}';

  try {
    showBullBearLoadingDialog(context, message: "Fetching market data...");

    final res = await http.get(Uri.parse(url));

    if (res.statusCode == 200) {
      final data = json.decode(res.body);
      print("Fetched Market ChethanSunny: $symbol - $expiry - $strike");
      print(data);

      setState(() {
        selectedExpiry = "";
        selectedStrike = 0.0;
      });

      if (data['results'] != null && data['results'].isNotEmpty) {
        final updatedMarket = MarketModel.fromJson(data['results'][0]);
        final id = updatedMarket.id.toString();

        context.go('/dashboard/stock-profile?id=$id');

        // ✅ Optionally update Riverpod state
        // ref.read(updateSingleMarketProvider)(updatedMarket);
      } else {
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
    print("Error fetching updated market: $e");
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Something went wrong while fetching market data."),
          backgroundColor: Colors.redAccent,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  } finally {
    hideBullBearDialog(context);
  }
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


 

  

  @override
  void initState() {
    onInit(
      () {
        // ref.read(getMarketsProvider.notifier).get();
       ref.read(getMarketsProviderNew.notifier).get();
      },
    );
    
    // Listen for odds type changes from settings
    ref.listen<String>(oddsTypeProvider, (previous, next) {
      if (previous != next) {
        setState(() => preferredOdds = next);
      }
    });

    super.initState();
  }


String preferredOdds = 'D'; // Default to Decimal

Future<void> loadPreferredOddsType() async {
  final prefs = await SharedPreferences.getInstance();
  final saved = prefs.getString('odds_type');
  print('DEBUG: Loaded odds_type from SharedPrefs: $saved');
  if (saved != null && ['A', 'D', 'F', 'P'].contains(saved)) {
    setState(() {
      preferredOdds = saved;
      print('DEBUG: preferredOdds set to: $preferredOdds');
    });
  } else {
    print('DEBUG: Odds type not found or invalid, using default D. Saved value: $saved');
  }
}

String getOdds(String? a, String? d, String? f, {double? impliedOdds}) {
  print('DEBUG getOdds called: preferredOdds=$preferredOdds, impliedOdds=$impliedOdds, a=$a, d=$d, f=$f');
  switch (preferredOdds) {
    case 'A':
      return a ?? 'N/A';
    case 'F':
      return f ?? 'N/A';
    case 'P':
      // Convert implied probability to percentage and format
      print('DEBUG getOdds P branch: impliedOdds=$impliedOdds');
      if (impliedOdds != null && impliedOdds > 0) {
        final probability = impliedOdds * 100;
        print('DEBUG getOdds P: calculated probability=$probability%');
        return '${probability.toStringAsFixed(2)}%';
      }
      // Fallback to decimal if implied odds not available
      print('DEBUG getOdds P: impliedOdds is null or 0, falling back to decimal: $d');
      return d ?? 'N/A';
    case 'D':
    default:
      return d ?? 'N/A';
  }
}

String formatToMMDDYYYY(String input) {
  final date = DateFormat('yyyy-MM-dd').parse(input);
  return DateFormat('MMM d, yyyy').format(date);
}


  @override
  void dispose() {
    _scrollController.dispose(); // Always dispose your controller!
    super.dispose();
  }

@override
  Widget build(BuildContext context) {
    final state = ref.watch(getMarketsProviderNew);
//  "",
   return Padding(
  padding: const EdgeInsets.only(left: 40),
  child: Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      border: Border.all(color: Color(0xFF1F242C)),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        /// 🔒 Fixed heading
        const Padding(
          padding: EdgeInsets.only(bottom: 12.0),
          child: Text(
            "All Available Markets",
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
        ),

         Expanded(
          child: ScrollbarTheme(
            data: ScrollbarThemeData(
              thumbColor: WidgetStateProperty.all(Colors.white54),
              thickness: WidgetStateProperty.all(6),
              radius: const Radius.circular(10),
              trackVisibility: WidgetStateProperty.all(true),
            ),
                      child: Scrollbar(
              thumbVisibility: true,
              controller: _scrollController,
              thickness: 6,
               radius: const Radius.circular(10),
              trackVisibility: true,
              interactive: true,
              child: state is LoadingState
                  ? const Center(child: LoadingMainCard())
                  : state is ErrorState
                      ? Text('Error: ${state.errorMessage}', style: const TextStyle(color: Colors.red))
                      : state is SuccessState
                          ? ListView.builder(
                              controller: _scrollController,
                              itemCount: state.data.results.length,
                              itemBuilder: (context, index) {
                                final market = state.data.results[index];
                                final marketKey = marketKeys.putIfAbsent(market.id!, () => GlobalKey());
                                // This gets all selected stocks from your Riverpod provider
                                  final selectedStocks = ref.watch(selectedStockProvider);

                                  // Check if "Over" is selected for this market
                                  final isOverSelected = selectedStocks.any(
                                    (s) => s.marketId == market.id && s.chosenOutcome == "over",
                                  );

                                  // Check if "Under" is selected for this market
                                  final isUnderSelected = selectedStocks.any(
                                    (s) => s.marketId == market.id && s.chosenOutcome == "under",
                                  );
                                return KeyedSubtree(
                                   key: marketKey,
                                  child: Container(
                                    // key: ValueKey(market.id),
                                    margin: const EdgeInsets.only(bottom: 12),
                                    padding: const EdgeInsets.only(  top:16),
                                    decoration: BoxDecoration(
                                      border: Border.all(color:  Color(0xFF1F242C)),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Column(
                                      
                                      children: [
                                        Row(
                                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                  
                                          children: [
                                            /// LEFT SIDE
                                             Padding(
                                               padding: const EdgeInsets.only(left:16.0),
                                               child: Column(
                                                  crossAxisAlignment: CrossAxisAlignment.start,
                                                  children: [
                                                    Row(
                                                      children: [
                                                     MouseRegion(
                                                          cursor: SystemMouseCursors.click,
                                                       child: GestureDetector(
                                                              onTap: () {
                                                                 String id = market.id.toString();
                                                                 context.go('/dashboard/stock-profile?id=$id');
                                                              },
                                                              child:  (market.stock.logoUrl != null)?
                                                                                                         ClipRRect(
                                                        borderRadius: BorderRadius.circular(6), // adjust for roundness
                                                        child: Image.network(
                                                          market.stock.logoUrl!,
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
                                                          (market.stock.symbol.length >= 2
                                                              ? market.stock.symbol.substring(0, 2)
                                                              : market.stock.symbol)
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
                                                     ),
                                                                                     
                                                        const SizedBox(width: 10),
                                                       Column(
                                                        crossAxisAlignment: CrossAxisAlignment.start,
                                                        children: [
                                                          /// Row for company name and symbol
                                                          Row(
                                                            crossAxisAlignment: CrossAxisAlignment.center,
                                                            children: [
                                                              if (market.stock.companyName != null)
                                                                Text(
                                                                  "${market.stock.companyName!} - ",
                                                                  style: const TextStyle(
                                                                    fontSize: 14,
                                                                    color: Colors.white,
                                                                    fontWeight: FontWeight.w500,
                                                                  ),
                                                                ),
                                                              Text(
                                                                "\$${market.stock.symbol}",
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
                                                            "\$${market.targetPrice.toStringAsFixed(2)}",
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
                                           
                                                    
                                            /// RIGHT SIDE
                                                                  Padding(
                                                                    padding: const EdgeInsets.only(right:16.0),
                                                                    child: Row(
                                                                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                                                          children: [
                                                    /// OVER BLOCK
                                                    Column(
                                                      children: [
                                                        // Top Label Box
                                                        Container(
                                                          width: 100,
                                                          padding: const EdgeInsets.symmetric(vertical: 6),
                                                          decoration:   BoxDecoration(
                                                                                                                      color:isOverSelected ? Colors.white : const Color(0xFF1F242C), 
                                  
                                                            borderRadius: BorderRadius.only(
                                                              topLeft: Radius.circular(8),
                                                              topRight: Radius.circular(8),
                                                            ),
                                                          ),
                                                          child:   Center(
                                                            child: Text(
                                                              "Over",
                                                              style: TextStyle(
                                                                color:isOverSelected ?  Color(0xFF1F242C): Color(0xFFD3D3D3),
                                                                fontSize: 12,
                                                                fontWeight: FontWeight.w500,
                                                              ),
                                                            ),
                                                          ),
                                                        ),
                                                        const SizedBox(height: 4), // 🔻 Margin between label and value
                                                        // Bottom Value Box
                                                        MouseRegion(
                                                          cursor: SystemMouseCursors.click,
                                                          child: GestureDetector(
                                                            onTap: () async {
                                                                    if (!checkMarketOpenOrAlert(context)) return;
                                                                                            
                                                                    final selectedStocks = ref.read(selectedStockProvider);
                                                                                            
                                                                    final alreadySelected = selectedStocks.any(
                                                                      (s) => s.marketId == market.id && s.chosenOutcome == "over",
                                                                    );
                                                                                            
                                                                    if (alreadySelected) {
                                                                      // 🔴 Just remove without any fetch
                                                                      ref.read(selectedStockProvider.notifier).remove(market.id);
                                                                    } else {
                                                                      // ✅ Fetch current page again, find updated market, and insert
                                                                      await fetchAndReplaceMarket(
                                                                        market.stock.symbol,
                                                                        market.expiryDate,
                                                                        market.targetPrice,
                                                                        "over",
                                                                        market.id, 
                                                                      );
                                                                    }
                                                                                            
                                                                    // (Optional) Debug print
                                                                    final currentList = ref.read(selectedStockProvider);
                                                                    for (var item in currentList) {
                                                                      print(item.toJson());
                                                                    }
                                                                  },
                                                            child: Container(
                                                              width: 100,
                                                              padding: const EdgeInsets.symmetric(vertical: 10),
                                                              decoration:   BoxDecoration(
                                                                color:isOverSelected ? Colors.white : const Color(0xFF1F242C),
                                                                borderRadius: BorderRadius.only(
                                                                  bottomLeft: Radius.circular(8),
                                                                  bottomRight: Radius.circular(8),
                                                                ),
                                                              ),
                                                              child: Center(
                                                                child: Text(
                                                                 getOdds(market.oddsAOver, market.oddsDOver, market.oddsFOver, impliedOdds: double.tryParse(market.impliedOddsOver)),
                                                                  style:   TextStyle(
                                                                    color:isOverSelected?Color(0xFF1F242C): Colors.white,
                                                                    fontSize: 14,
                                                                    fontWeight: FontWeight.bold,
                                                                  ),
                                                                ),
                                                              ),
                                                            ),
                                                          ),
                                                        ),
                                                      ],
                                                    ),
                                                
                                                            const SizedBox(width: 12),
                                                
                                                            /// UNDER BLOCK
                                                            Column(
                                                              children: [
                                                                // Top Label Box
                                                                Container(
                                                                  width: 100,
                                                                  padding: const EdgeInsets.symmetric(vertical: 6),
                                                                  decoration:   BoxDecoration(
                                                                    color: isUnderSelected ? Colors.white : const Color(0xFF1F242C), 
                                                                    borderRadius: BorderRadius.only(
                                                                      topLeft: Radius.circular(8),
                                                                      topRight: Radius.circular(8),
                                                                    ),
                                                                  ),
                                                                  child:   Center(
                                                                    child: Text(
                                                                      "Under",
                                                                      style: TextStyle(
                                                                        color:isUnderSelected?Color(0xFF1F242C): Color(0xFFD3D3D3),
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
                                                                      onTap: () async {
                                                                    if (!checkMarketOpenOrAlert(context)) return;
                                                                                                    
                                                                    final selectedStocks = ref.read(selectedStockProvider);
                                                                                                    
                                                                    final alreadySelected = selectedStocks.any(
                                                                      (s) => s.marketId == market.id && s.chosenOutcome == "under",
                                                                    );
                                                                                                    
                                                                    if (alreadySelected) {
                                                                      // 🔴 Just remove — no refetching
                                                                      ref.read(selectedStockProvider.notifier).remove(market.id);
                                                                    } else {
                                                                      // ✅ Fetch updated market from server and insert selection
                                                                      await fetchAndReplaceMarket(
                                                                        market.stock.symbol,
                                                                        market.expiryDate,
                                                                        market.targetPrice,
                                                                        "under",
                                                                        market.id, 
                                                                      );
                                                                    }
                                                                                                    
                                                                    // (Optional) Debug log
                                                                    final currentList = ref.read(selectedStockProvider);
                                                                    for (var item in currentList) {
                                                                      print(item.toJson());
                                                                    }
                                                                  },
                                                                    child: Container(
                                                                      width: 100,
                                                                      padding: const EdgeInsets.symmetric(vertical: 10),
                                                                      decoration:   BoxDecoration(
                                                                        color: isUnderSelected ? Colors.white : const Color(0xFF1F242C) ,
                                                                        borderRadius: BorderRadius.only(
                                                                          bottomLeft: Radius.circular(8),
                                                                          bottomRight: Radius.circular(8),
                                                                        ),
                                                                      ),
                                                                      child: Center(
                                                                        child: Text(
                                                                          getOdds(market.oddsAUnder, market.oddsDUnder, market.oddsFUnder, impliedOdds: double.tryParse(market.impliedOddsUnder)),
                                                                          style:   TextStyle(
                                                                            color:isUnderSelected?Color(0xFF1F242C): Colors.white,
                                                                            fontSize: 14,
                                                                            fontWeight: FontWeight.bold,
                                                                          ),
                                                                        ),
                                                                      ),
                                                                    ),
                                                                  ),
                                                                ),
                                                              ],
                                                            ),
                                                
                                                                     
                                                                         const SizedBox(height: 12), // spacing between main row and new info row
                                                                     
                                                                     /// New Bottom Row: Expiry & Stock Info
                                                                    
                                                                     
                                                                       ],
                                                                     ),
                                                                  ),
                                                                
                                        
                                        
                                        
                                        
                                          ],
                                        ),
                                         Container(
                                         padding:   EdgeInsets.only(left:20, right: 40, top: 15.0, bottom: 15.0),
                                          margin: const EdgeInsets.only(top: 8),
                                          decoration: BoxDecoration(
                                            color: const Color(0xFF1F242C),
                                           borderRadius: const BorderRadius.only(
                                            bottomLeft: Radius.circular(8),
                                            bottomRight: Radius.circular(8),
                                            ),
                                          ),
                                          child:  Row(
                                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                              children: [
                                                /// Expiry Left
                                                GestureDetector(
                                                  onTap: () async {
                                                    await _openExpiryDialog(market.stock.symbol.toString());
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
                                                              text: formatExpiryDate(market.expiryDate),
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
                                                        final parsedDate = inputFormat.parse(market.expiryDate);
                                                        final formattedExpiry = outputFormat.format(parsedDate);

                                                        await _openStrikePriceDialog(market.stock.symbol, formattedExpiry);
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
                                                              text: "\$${market.targetPrice.toStringAsFixed(2)}",
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
                                   
                                  
                                       
                                      ],
                                    ),
                                  ),
                                );
                              },
                            )
                          : const Text('No data'),
            ),
          ),
        ),
        (state is SuccessState)
    ?  Row(
  mainAxisAlignment: MainAxisAlignment.center,
  children: [
    if (state.data.totalPages <= 6) ...[
      for (int i = 1; i <= state.data.totalPages; i++)
        _buildPageButton(
          page: i,
          currentPage: currentPage!,
          onPressed: () async {
            final pageStr = i.toString();
            setState(() => currentPage = pageStr);

            final prefs = await SharedPreferences.getInstance();
            await prefs.setString('allStocksPage', pageStr);

            ref.read(getMarketsProviderNew.notifier).get(
              queryParams: {'page': pageStr},
            );
          },
        ),
    ] else ...[
      _buildPageButton(
        page: 1,
        currentPage: currentPage!,
        onPressed: () async {
          setState(() => currentPage = '1');

          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('allStocksPage', '1');

          ref.read(getMarketsProviderNew.notifier).get(
            queryParams: {'page': '1'},
          );
        },
      ),

      if (int.parse(currentPage!) > 4)
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 4),
          child: Text("...", style: TextStyle(color: Colors.white)),
        ),

      for (int i = int.parse(currentPage!) - 1;
          i <= int.parse(currentPage!) + 1;
          i++)
        if (i > 1 && i < state.data.totalPages)
          _buildPageButton(
            page: i,
            currentPage: currentPage!,
            onPressed: () async {
              final pageStr = i.toString();
              setState(() => currentPage = pageStr);

              final prefs = await SharedPreferences.getInstance();
              await prefs.setString('allStocksPage', pageStr);

              ref.read(getMarketsProviderNew.notifier).get(
                queryParams: {'page': pageStr},
              );
            },
          ),

      if (int.parse(currentPage!) < state.data.totalPages - 3)
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 4),
          child: Text("...", style: TextStyle(color: Colors.white)),
        ),

      _buildPageButton(
        page: state.data.totalPages,
        currentPage: currentPage!,
        onPressed: () async {
          final last = state.data.totalPages.toString();
          setState(() => currentPage = last);

          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('allStocksPage', last);

          ref.read(getMarketsProviderNew.notifier).get(
            queryParams: {'page': last},
          );
        },
      ),
    ],
  ],
)

    : const Text("")

      ],
    ),
  ),
);

  }
}



Widget _buildPageButton({
  required int page,
  required String currentPage,
  required VoidCallback onPressed,
}) {
  final isActive = currentPage == page.toString();

  return Padding(
    padding: const EdgeInsets.symmetric(horizontal: 4.0),
    child: TextButton(
      onPressed: onPressed,
      style: TextButton.styleFrom(
        backgroundColor: isActive ? Colors.white : const Color(0xFF1f242c),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(
            color: Colors.white,
          ),
        ),
      ),
      child: Text(
        page.toString(),
        style: TextStyle(
          color: isActive ? const Color(0xFF1f242c) : Colors.white,
        ),
      ),
    ),
  );
}
