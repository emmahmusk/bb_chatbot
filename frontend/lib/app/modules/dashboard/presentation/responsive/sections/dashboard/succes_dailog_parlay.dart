import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:frontend/app/shared/functions/date_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:go_router/go_router.dart';
class ParlaySuccessDialog extends StatelessWidget {
  final List<ParlayBetItem> bets;
  final String wagerAmount;
  final String potentialPayout;
  final String odds;

  const ParlaySuccessDialog({
    super.key,
    required this.bets,
    required this.wagerAmount,
    required this.potentialPayout,
    required this.odds
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.pop(context),
      child: Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(20),
        child: Stack(
          alignment: Alignment.center,
          children: [
            BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
              child: Container(),
            ),
             Container(
                width: 400.0,
                decoration: BoxDecoration(
                  color: const Color(0xFF1F242C),
                  borderRadius: BorderRadius.circular(16),
                ),
                clipBehavior: Clip.hardEdge,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 600), // or MediaQuery if dynamic
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              ClipRect(
                                child: Align(
                                  alignment: Alignment.bottomCenter,
                                  heightFactor: 0.9, // shows only bottom 90% (crops top 10%)
                                  child: Image.asset(
                                    'assets/media/pngs/success_slip.png',
                                    width: double.infinity,
                                    fit: BoxFit.cover,
                                  ),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                                color: Colors.transparent, // fully transparent
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: const [
                                    Text(
                                      'Parlay Placed',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 17,
                                        fontWeight: FontWeight.bold,
                                        shadows: [Shadow(color: Colors.black, blurRadius: 4)],
                                      ),
                                    ),
                                    SizedBox(height: 4),
                                    Text(
                                      'Your Parlay has been successfully placed. All legs are live!',
                                      style: TextStyle(
                                        color: Colors.white70,
                                        fontSize: 13,
                                        shadows: [Shadow(color: Colors.black, blurRadius: 4)],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),


                        const SizedBox(height: 10),
                    
                       // ✅ Horizontal scrollable bet cards
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            child: SizedBox(
                              height: 150,
                              width: double.infinity,
                              child: ScrollConfiguration(
                                behavior: ScrollConfiguration.of(context).copyWith(
                                  dragDevices: {
                                    PointerDeviceKind.touch,
                                    PointerDeviceKind.mouse,
                                    PointerDeviceKind.stylus,
                                    PointerDeviceKind.trackpad,
                                  },
                                ),
                                child: SingleChildScrollView(
                                  scrollDirection: Axis.horizontal,
                                  primary: false, // important when nested in another scroll view
                                  physics: const BouncingScrollPhysics(),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min, // let Row be only as wide as children
                                    children: bets.map((item) {
                                      return Container(
                                        width: 220,
                                        margin: const EdgeInsets.only(right: 12),
                                        padding: const EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFF2B313C),
                                          borderRadius: BorderRadius.circular(12),
                                          border: Border.all(color: Colors.grey.shade700),
                                        ),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Row(
                                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                              children: [
                                                const Text('Ticker', style: TextStyle(color: Colors.white)),
                                                Row(
                                                  children: [
                                                    CircleAvatar(
                                                      backgroundImage: NetworkImage(item.logoUrl),
                                                      radius: 10,
                                                      backgroundColor: Colors.transparent,
                                                    ),
                                                    const SizedBox(width: 6),
                                                    Text('\$${item.tickerSymbol}',
                                                        style: const TextStyle(color: Colors.white)),
                                                  ],
                                                ),
                                              ],
                                            ),
                                            const SizedBox(height: 5),
                                            infoRow(
                                              'Exp Date',
                                              formatDateToNam(item.expiryDate),
                                            ),
                                            infoRow('Odds', item.odds),
                                          ],
                                        ),
                                      );
                                    }).toList(),
                                  ),
                                ),
                              ),
                            ),
                          ),


                    
                    
                    
                    
                    
                        const SizedBox(height: 10),
                    
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 5.0),
                          child: Divider(
                            color: Colors.grey.shade400,
                            thickness: 1,
                          ),
                        ),
                    
                        infoRowStyled('Wager Amount', wagerAmount, isGreen: true),
                        infoRowStyled('Odds', odds, isGreen: false),
                        infoRowStyled('Potential Payout', potentialPayout, isGreen: true),
                    
                        const SizedBox(height: 10),
                    
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 5.0),
                          child: CustomButton(
                            text: 'Go home',
                            onPressed: () {
                              Navigator.pop(context);
                              context.go('/dashboard/trending');
                            },
                          ),
                        ),
                        const SizedBox(height: 10),
                      ],
                    ),
                  ),
                ),
              ),
            
          ],
        ),
      ),
    );
  }

  Widget infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.white)),
          Text(value, style: const TextStyle(color: Colors.white)),
        ],
      ),
    );
  }

  Widget infoRowStyled(String label, String value, {bool isGreen = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 5.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.w600,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              color: isGreen ? Colors.greenAccent : Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

class ParlayBetItem {
  final String tickerSymbol;
  final String logoUrl;
  final String expiryDate;
  final String odds;

  ParlayBetItem({
    required this.tickerSymbol,
    required this.logoUrl,
    required this.expiryDate,
    required this.odds,
  });
}
