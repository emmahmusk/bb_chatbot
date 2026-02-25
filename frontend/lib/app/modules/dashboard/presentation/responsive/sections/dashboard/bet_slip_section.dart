import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/modules/dashboard/data/dtos/parlay_bet_dto.dart';
import 'package:frontend/app/modules/dashboard/data/dtos/single_bet_dto.dart';
import 'package:frontend/app/modules/dashboard/data/models/markets_model.dart';
import 'package:frontend/app/modules/dashboard/domain/repositories/dashboard_repository.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/get_bet_list_provider.dart';
import 'package:frontend/app/modules/dashboard/presentation/widgets/trending/bet_slip_item.dart';
import 'package:frontend/app/shared/functions/alert_functions.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_textfield.dart';
import 'package:frontend/app/shared/presentation/widgets/empty_state.dart';
import 'package:frontend/app/shared/presentation/widgets/row_title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
 
import 'package:go_router/go_router.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/stock_selection_provider.dart';
import 'dart:developer';
import 'dart:convert'; 
import 'dart:math';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'success_dailog.dart';
import 'succes_dailog_parlay.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/classes/preferences/preferences.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';

class BetSlipSection extends ConsumerStatefulWidget {
  const BetSlipSection({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _BetSlipSectionState();
}

class _BetSlipSectionState extends ConsumerState<BetSlipSection> {
  final List<String> tabs = ['Single', 'Parlay'];
  int? _manuallySelectedIndex;

  String wager = '';
String selectedMode = 'single';

Key wagerFieldKey = UniqueKey();
  double maxRiskTolerance = 3000.0; // default fallback
  final Map<int, Map<String, double>> marketExposures = {}; // marketId -> {'net': net_exposure, 'over': x, 'under': y, 'override': flag}

  @override
  void initState() {
    super.initState();
    // fetch platform settings and listen for selected stock changes
    fetchPlatformSettings();
    // Listen to selectedStockProvider to fetch market exposures when selections change
    ref.listen<List>(selectedStockProvider, (prev, next) {
      try {
        for (var s in next) {
          if (s is Map) continue; // defensive
          final marketId = s.marketId;
          // Always fetch to get fresh exposure data on selection change
          fetchMarketExposure(marketId);
        }
      } catch (_) {}
    });
    // Also fetch exposures for any already-selected stocks (initial state)
    try {
      final currentlySelected = ref.read(selectedStockProvider);
      for (var s in currentlySelected) {
        if (s is Map) continue;
        final marketId = s.marketId;
        // Fetch initial exposures
        fetchMarketExposure(marketId);
      }
    } catch (_) {}
  }

  Future<void> fetchPlatformSettings() async {
    try {
      final res = await http.get(Uri.parse('https://api.bbbprediction.com/admin/platform_settings/'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final val = data['max_risk_tolerance'];
        if (val != null) {
          setState(() {
            maxRiskTolerance = double.tryParse(val.toString()) ?? maxRiskTolerance;
          });
        }
      }
    } catch (e) {
      // ignore - keep default
    }
  }

  Future<void> fetchMarketExposure(int marketId) async {
    try {
      final res = await http.get(Uri.parse('https://api.bbbprediction.com/bet/markets/$marketId/'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final over = data['exposure_over'];
        final under = data['exposure_under'];
        final net = data['net_exposure'];
        final overrideFlag = data['requires_admin_override'] == true;
        setState(() {
          marketExposures[marketId] = {
            'over': over != null ? double.tryParse(over.toString()) ?? 0.0 : 0.0,
            'under': under != null ? double.tryParse(under.toString()) ?? 0.0 : 0.0,
            'net': net != null ? double.tryParse(net.toString()) ?? 0.0 : 0.0,
            'override': overrideFlag ? 1.0 : 0.0,
          };
        });
      }
    } catch (e) {
      // ignore
    }
  }

  
  double estimatePayout(double wager, int count) {
    if (wager <= 0 || count == 0) return 0.0;
    double odds = 1.0;
    final random = Random();
    for (int i = 0; i < count; i++) {
      odds *= (1.7 + random.nextDouble() * 0.3); // between 1.7–2.0
    }
    return wager * odds;
  }


  @override
  Widget build(BuildContext context) {

    final selectedStocks = ref.watch(selectedStockProvider);

      final double wagerAmount = double.tryParse(wager) ?? 0.0;
    final double payout = wagerAmount * getCumulativeOdds(selectedStocks);

    final colors = ref.watch(appThemeProvider).colors;
    final betList = ref.watch(betListProvider);

    ref.listen(betListProvider, (prev, next) {
      _manuallySelectedIndex = null;
      setState(() {});
    });

    int autoIndex = betList.length > 1 ? 1 : 0;
    int currentIndex = _manuallySelectedIndex ?? autoIndex;

    setState(() {});

    return SingleChildScrollView(
      child: Container(
        // height: double.maxFinite,
        decoration: BoxDecoration(
          border: Border.all(color: colors.always30363D),
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(16),
            topRight: Radius.circular(16),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 68,
              width: double.maxFinite,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(16),
                  topRight: Radius.circular(16),
                ),
                color: colors.always1F242C,
              ),
              child: Text(
                'Bet Slip',
                style: TextStyle(
                  color: colors.alwaysWhite,
                  fontWeight: FontWeight.w400,
                  fontSize: 24,
                ),
              ),
            ),
             
             Padding(
  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
  child: selectedStocks.isEmpty
      ? IndexedStack(
          index: currentIndex,
          children: [
            SingleChildScrollView(child: SingleView()),
            SingleChildScrollView(child: ParlayView()),
          ],
        )
      : Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
             if (selectedStocks.isNotEmpty) ...[
  Row(
    mainAxisAlignment: MainAxisAlignment.start,
    children: [
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: selectedStocks.length == 1 ? Colors.white : Colors.black,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selectedStocks.length == 1 ? Colors.black : Colors.white,
          ),
        ),
        child: Text(
          'Single',
          style: TextStyle(
            color: selectedStocks.length == 1 ? Colors.black : Colors.white,
          ),
        ),
      ),
      const SizedBox(width: 10),
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: selectedStocks.length > 1 ? Colors.white : Colors.black,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selectedStocks.length > 1 ? Colors.black : Colors.white,
          ),
        ),
        child: Text(
          'Parlay',
          style: TextStyle(
            color: selectedStocks.length > 1 ? Colors.black : Colors.white,
          ),
        ),
      ),
    ],
  ),
  const SizedBox(height: 12),
],

           
             
            ListView.builder(
        shrinkWrap: true,
        itemCount: selectedStocks.length,
        itemBuilder: (context, index) {
          final item = selectedStocks[index];
          return Stack(
            children: [
              Container(
                margin: const EdgeInsets.all(8.0),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.shade800),
                  borderRadius: BorderRadius.circular(12),
                  color:  Color(0xFF1F242C)
                ),
                child: Column(
                  children: [
              
                    Padding(
                                                 padding: const EdgeInsets.only(left:10.0),
                                                 child: Column(
                                                    crossAxisAlignment: CrossAxisAlignment.start,
                                                    children: [
                                                      Row(
                                                        children: [
                                                       GestureDetector(
                                                              onTap: () {
                                                               
                                                              },
                                                              child:  ( item.logoUrl!= null)?
                                                    ClipRRect(
                                                        borderRadius: BorderRadius.circular(6), // adjust for roundness
                                                        child: Image.network(
                                                          item.logoUrl,
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
                                                          (  item.companySymbol.length >= 2
                                                              ? item.companySymbol.substring(0, 2)
                                                              : item.companySymbol)
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
                                                                if (item.companyName != null)
                                                                  SizedBox(
                                                                    width: min(MediaQuery.of(context).size.width * 0.5, 200),
                                                                    child: Text(
                                                                      "${item.companyName!} ",
                                                                      overflow: TextOverflow.ellipsis,
                                                                      style: const TextStyle(
                                                                        fontSize: 14,
                                                                        color: Colors.white,
                                                                        fontWeight: FontWeight.w500,
                                                                      ),
                                                                    ),
                                                                  ),
                                                                // Text(
                                                                //   "\$${ item.companySymbol}",
                                                                //   style: const TextStyle(
                                                                //     fontSize: 14,
                                                                //     color: Color(0xFF888888), // dark gray
                                                                //     fontWeight: FontWeight.w500,
                                                                //   ),
                                                                // ),
                                                              ],
                                                            ),
                                                                                       
                                                            const SizedBox(height: 4), // spacing between rows
                                                                                       
                                                            /// Strike price on a new line
                                                            Text(
                                                              "\$${item.companySymbol}",
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
                  const SizedBox(height: 16),
                                Padding(
                                      padding:EdgeInsetsGeometry.only(left: 10.0,right: 10.0), 
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                                  Text("Strike Price:",style: TextStyle(color: Colors.white),),
                                                  Row(
                                                    mainAxisSize: MainAxisSize.min,
                                                    children: [
                                                      Text(item.chosenOutcome+" - "+"\$"+item.targetPrice.toString(),style: TextStyle(color: Colors.white),),
                                                      const SizedBox(width: 8),
                                                      // show padlock when that side is locked based on net_exposure
                                                      Builder(builder: (ctx) {
                                                        final exposures = marketExposures[item.marketId];
                                                        bool locked = false;
                                                        if (exposures != null) {
                                                          final netExposure = exposures['net'] ?? 0.0;
                                                          final overrideFlag = (exposures['override'] ?? 0.0) >= 1.0;
                                                          // Locked if net_exposure >= maxRiskTolerance or admin override
                                                          if (overrideFlag || netExposure >= maxRiskTolerance) locked = true;
                                                        }
                                                        return locked
                                                            ? Tooltip(
                                                                message: 'Market locked due to net exposure limit',
                                                                child: Icon(
                                                                  Icons.lock,
                                                                  size: 16,
                                                                  color: Colors.redAccent,
                                                                ),
                                                              )
                                                            : SizedBox.shrink();
                                                      }),
                                                    ],
                                                  ),
                                        ],
                                      ),
                                ),
                                const SizedBox(height: 8),
                                Padding(
                                  padding: EdgeInsetsGeometry.only(left: 10.0,right: 10.0), 
                                  child: const Divider(color: Colors.grey, thickness: 1),
                                ), // dark grey line
                                const SizedBox(height: 8),
                                Padding(
                                      padding:EdgeInsetsGeometry.only(left: 10.0,right: 10.0), 
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          Text("Exp Date:",style: TextStyle(color: Colors.white),),
                                          Text(item.expiryDate ,style: TextStyle(color: Colors.white),)
                                        ],
                                      ),
                                ),
                                const SizedBox(height: 8),
                                Padding(
                                  padding: EdgeInsetsGeometry.only(left: 10.0,right: 10.0), 
                                  child: const Divider(color: Colors.grey, thickness: 1),
                                ), // dark grey line
                                const SizedBox(height: 8),
                                Padding(
                                      padding:EdgeInsetsGeometry.only(left: 10.0,right: 10.0), 
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          Text("Odd:",style: TextStyle(color: Colors.white),),
                                          Text(item.odds.toString() ,style: TextStyle(color: Colors.white),)
                                        ],
                                      ),
                                ),
                    // 
                    
                  ],
                ),
              ),
              Positioned(
                top: 15,
                right: 15,
                child: MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () {
                      ref.read(selectedStockProvider.notifier).remove(item.marketId);
                    },
                    child: const Icon(
                      Icons.close,
                      size: 16,
                      color: Colors.white70,
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      )

          ],
        ),
),
             
            Container(
              width: double.maxFinite,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: colors.always1F242C,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                selectedStocks.length!=0?CustomTextField(
                    key: wagerFieldKey,
                    headerText: 'Wager Amount',
                    hint: 'Enter Wager Amount',
                    onChanged: (v) {
                      wager = v;
                      setState(() {});
                    },
                    keyboardType: TextInputType.number,
                    textInputAction: TextInputAction.done,
                    textFieldColor: colors.always161B22,
                    borderColor: colors.always30363D,
                    hasPrefixSpace: true,
                    prefix: Text(
                      '\$',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w400,
                        color: colors.always6E7681,
                      ),
                    ),
                    validator: (value) {
                      if (value.isEmpty) {
                        return 'Wager amount is required';
                      }
      
                      final numericValue = double.tryParse(value);
                      if (numericValue == null) {
                        return 'Please enter a valid number';
                      }
      
                      if (numericValue <= 0) {
                        return 'Wager must be greater than 0';
                      }
      
                      if (numericValue > 500) {
                        return 'Wager cannot exceed \$500';
                      }
      
                      return null; // Valid input
                    },
                    inputFormatters: [
                      FilteringTextInputFormatter.allow(
                        RegExp(r'^\d*\.?\d{0,2}'),
                      ),
                    ],
                  ):SizedBox.shrink() ,
                  const SizedBox(height: 12),
                  CustomDivider(),
                  const SizedBox(height: 12),
                 RowTitleSubtitle(
                    title: 'Cumulative Odds',
                    subtitle: wagerAmount!=0?  getCumulativeOdds(selectedStocks).toStringAsFixed(2):"0.00",
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Payout on Win',
                        style: TextStyle(
                          fontSize: 18,
                          color: colors.alwaysWhite,
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Clickable(
                      //   child: Icon(
                      //     Icons.info_outline,
                      //     size: 16,
                      //     color: colors.always8B949E,
                      //   ),
                      // ),
                      const Spacer(),
                      Text(
                        wagerAmount!=0? '\$${payout.toStringAsFixed(2)}':"\$0.00",
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                          // color: colors.always27D07F,
                          color: colors.alwaysWhite,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            selectedStocks.length!=0?  SizedBox(height: 24):SizedBox.shrink(),
            selectedStocks.length!=0? Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: CustomButton(
                  text: 'Place Bet',
                  validator: () {
                    // Disable if net_exposure >= maxRiskTolerance for any selected leg
                    if (wager.isEmpty) return false;
                    for (final s in selectedStocks) {
                      final exposures = marketExposures[s.marketId];
                      if (exposures != null) {
                        final netExposure = exposures['net'] ?? 0.0;
                        if (netExposure >= maxRiskTolerance) return false;
                      }
                    }
                    return true;
                  },
                  onPressed: () async {
                    if (!isAuthenticated()) {
                      showCenterDialog(context, child: const LoginDialog());
                      
                      
                      return;
                    }
      
                    final repo = ref.read(dashboardRepositoryProvider);
                    final double? wagerAmount = double.tryParse(wager);
      
                    if (wagerAmount == null || wagerAmount <= 0) {
                      showTopRightAlert(
                          context, "Enter a valid wager amount.", true);
                      return;
                    }
      
                    final prefs = await SharedPreferences.getInstance();
                        final token = prefs.getString('access_token');

                        final selectedStocks = ref.read(selectedStockProvider);

                        // Prepare headers
                        final headers = {
                          'Content-Type': 'application/json',
                          'Authorization': 'Bearer $token',
                        };

                        try {
                          if (selectedStocks.length == 1) {
                            // 🟢 SINGLE BET API
                            final body = json.encode({
                              "market_id": selectedStocks.first.marketId,
                              "chosen_outcome": selectedStocks.first.chosenOutcome,
                              "amount_wagered": wagerAmount,
                            });

                            final res = await http.post(
                              Uri.parse('https://api.bbbprediction.com/bet/single/'),
                              headers: headers,
                              body: body,
                            );

                            print("Single Bet response");
                            
                            print(res.body);

                            if (res.statusCode == 200 || res.statusCode == 201) {
                                final currentUser = ref.read(currentUserProvider);

                               if (currentUser != null) {
                                final currentBalance = double.tryParse(currentUser.walletBalance) ?? 0.0;
                                final updatedBalance = (currentBalance - wagerAmount).clamp(0.0, double.infinity);

                                final updatedUser = Profile(
                                  id: currentUser.id,
                                  user: currentUser.user,
                                  emailVerified: currentUser.emailVerified,
                                  fullName: currentUser.fullName,
                                  email: currentUser.email,
                                  dateOfBirth: currentUser.dateOfBirth,
                                  phoneNumber: currentUser.phoneNumber,
                                  physicalAddress: currentUser.physicalAddress,
                                  walletBalance: updatedBalance.toStringAsFixed(2),
                                );

                                ref.read(currentUserProvider.notifier).state = updatedUser;

                                // Optionally update shared prefs if used elsewhere
                                final prefs = await SharedPreferences.getInstance();
                                await prefs.setString('wallet_balance', updatedBalance.toStringAsFixed(2));
                              }
                              showTopRightAlert(context, "Single bet placed!", false);
                                context.go('/dashboard/trending');        
                               await showDialog(
                                context: context,
                                useRootNavigator: true,
                                barrierDismissible: true,
                                barrierColor: Colors.black54,
                                builder: (_) => SuccessDialog(
                                  ticker: selectedStocks.first.companySymbol,
                                  expDate: selectedStocks.first.expiryDate,
                                  odds: getCumulativeOdds(selectedStocks).toStringAsFixed(2),
                                  wagerAmount: '\$${wagerAmount.toString()}',
                                  payout: '\$${payout.toStringAsFixed(2)}',
                                  logoUrl: selectedStocks.first.logoUrl,
                                  symbol: selectedStocks.first.companySymbol,
                                ),
                              );
                              Future.delayed(Duration(milliseconds: 50), () {
                                setState(() {
                                    wager = '';
                                    wagerFieldKey = UniqueKey();  
                                  });
                                });
                                // ✅ Clear selection and input after success
                                ref.read(selectedStockProvider.notifier).clear();
                            } else {
                               
                              var  data = jsonDecode(res.body);
                              showTopRightAlert(context, "Failed: ${data['message']}", true);
                            }
                          } else if (selectedStocks.length > 1){
                            // 🔵 PARLAY BET API
                            final legs = selectedStocks.map((e) => {
                              "market_id": e.marketId,
                              "chosen_outcome": e.chosenOutcome,
                            }).toList();

                            final body = json.encode({
                              "amount_wagered": wager,
                              "legs": legs,
                            });

                            final res = await http.post(
                              Uri.parse('https://api.bbbprediction.com/bet/parlay/'),
                              headers: headers,
                              body: body,
                            );
                            
                            print("Parlay Bet response");
                            print(res.body);

                            // Show the Parlay Success Dialog
                            
                            if (res.statusCode == 200 || res.statusCode == 201) {
                              // ✅ Step 1: Subtract wager from wallet
                              final currentUser = ref.read(currentUserProvider);
                              if (currentUser != null) {
                                final currentBalance = double.tryParse(currentUser.walletBalance) ?? 0.0;
                                final updatedBalance = (currentBalance - wagerAmount).clamp(0.0, double.infinity);

                                final updatedUser = Profile(
                                  id: currentUser.id,
                                  user: currentUser.user,
                                  emailVerified: currentUser.emailVerified,
                                  fullName: currentUser.fullName,
                                  email: currentUser.email,
                                  dateOfBirth: currentUser.dateOfBirth,
                                  phoneNumber: currentUser.phoneNumber,
                                  physicalAddress: currentUser.physicalAddress,
                                  walletBalance: updatedBalance.toStringAsFixed(2),
                                );

                                ref.read(currentUserProvider.notifier).state = updatedUser;

                                // Optional: update shared preferences too
                                final prefs = await SharedPreferences.getInstance();
                                await prefs.setString('wallet_balance', updatedBalance.toStringAsFixed(2));
                              }
                              showTopRightAlert(context, "Parlay bet placed!", false);
                              // Create a list of ParlayBetItem(s)
                                List<ParlayBetItem> parlayItems = selectedStocks.map((stock) {
                                  return ParlayBetItem(
                                    tickerSymbol: stock.companySymbol,
                                    logoUrl: stock.logoUrl,
                                    expiryDate: stock.expiryDate,
                                    odds: stock.odds.toString(),
                                  );
                                }).toList();
                                showDialog(
                                  context: context,
                                  barrierDismissible: true,
                                  builder: (context) => ParlaySuccessDialog(
                                    bets: parlayItems,
                                    wagerAmount: "\$${wagerAmount.toStringAsFixed(0)}",
                                    odds: getCumulativeOdds(selectedStocks).toStringAsFixed(2),
                                    potentialPayout: "\$${ payout.toStringAsFixed(2)}",
                                  ),
                                );
                                Future.delayed(Duration(milliseconds: 50), () {
                                setState(() {
                                    wager = '';
                                    wagerFieldKey = UniqueKey();  
                                  });
                                });
                                // ✅ Clear selection and input after success
                                ref.read(selectedStockProvider.notifier).clear();

                                
                            } else {
                              // showTopRightAlert(context, "Failed: ${res.body}", true);
                              var  data = jsonDecode(res.body);
                              showTopRightAlert(context, "Failed: ${data['message']}", true);
                            }
                          }else{
                            print("Please select alteast once");
                          }

                          
                          
                       

                        } catch (e) {
                          showTopRightAlert(context, "Error occurred: $e", true);
                        }
                    // final responseFuture = betList.length == 1
                    //     ? repo.placeSingleBet(
                    //         SingleBetDto(
                    //           marketId: betList.first.id,
                    //           chosenOutcome: betList.first.outcomeType,
                    //           amountWagered: wagerAmount,
                    //         ),
                    //       )
                    //     : repo.placeParlayBet(
                    //         ParlayBetDto(
                    //           amountWagered: wager,
                    //           legs: betList
                    //               .map((bet) => ParlayLegDto(
                    //                     marketId: bet.id,
                    //                     chosenOutcome: bet.outcomeType,
                    //                   ))
                    //               .toList(),
                    //         ),
                    //       );
      
                    // perform(
                    //   context,
                    //   response: responseFuture,
                    //   onSuccess: (_) {
                    //     // Optional: show confirmation or clear state
                    //   },
                    // );
                  }),
            ):SizedBox.shrink(),
             selectedStocks.length!=0?  SizedBox(height: 24):SizedBox.shrink(),
          ],
        ),
      ),
    );
  }

  String getOddsBasedOnType(MarketModel market) {
    return market.outcomeType.toLowerCase() == "over"
        ? market.displayOddsOver
        : market.displayOddsUnder;
  }

  double getCumulativeOdds(List selectedList) {
    if (selectedList.isEmpty) return 0.0;
    if (selectedList.length == 1) {
      // Use decimal odds for calculation, fallback to displayed odds if not available
      final item = selectedList.first;
      final decimalOddsStr = item.decimalOdds ?? item.odds;
      return double.tryParse(decimalOddsStr?.toString() ?? '') ?? 1.0;
    }

    return selectedList
        .map((item) {
          // Use decimal odds for calculation, fallback to displayed odds if not available
          final decimalOddsStr = item.decimalOdds ?? item.odds;
          return double.tryParse(decimalOddsStr?.toString() ?? '') ?? 1.0;
        })
        .fold(1.0, (product, odd) => product * odd);
  }

}

class SingleView extends ConsumerStatefulWidget {
  const SingleView({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _SingleViewState();
}

class _SingleViewState extends ConsumerState<SingleView> {
  @override
  Widget build(BuildContext context) {
    final betList = ref.watch(betListProvider);
    if (betList.isEmpty || betList.length > 1) {
      return EmptyState(
        title: "Your Bet Slip is empty",
        message: "",
      );
    }
    return Column(
      children: [
        BetSlipItem(bet: betList.first),
      ],
    );
  }
}

class ParlayView extends ConsumerStatefulWidget {
  const ParlayView({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _ParlayViewState();
}

class _ParlayViewState extends ConsumerState<ParlayView> {
  @override
  Widget build(BuildContext context) {
    final betList = ref.watch(betListProvider);
    if (betList.isEmpty || betList.length < 2) {
      return EmptyState(
        title: "Your bet-slip is empty",
        message: "Excepteur sint occaecat cupidatat non proident, sunt",
      );
    }

    return   Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
           
          for (var bet in betList) ...[
            BetSlipItem(bet: bet),
            const SizedBox(height: 12),
          ],
        ],
      ) ;
  }
}
