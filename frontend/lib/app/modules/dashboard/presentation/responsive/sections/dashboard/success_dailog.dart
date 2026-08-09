import 'package:flutter/material.dart';
import 'package:frontend/app/shared/functions/date_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:go_router/go_router.dart';

class SuccessDialog extends StatelessWidget {
  final String ticker;
  final String expDate;
  final String odds;
  final String wagerAmount;
  final String payout;
  final String logoUrl;
  final String symbol;

  const SuccessDialog({
    super.key,
    required this.ticker,
    required this.expDate,
    required this.odds,
    required this.wagerAmount,
    required this.payout,
    required this.logoUrl,
    required this.symbol,
  });

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(20),
      child: Center(
        child: Container(
          width: 400.0,
          decoration: BoxDecoration(
            color: const Color(0xFF1F242C),
            borderRadius: BorderRadius.circular(16),
          ),
          clipBehavior: Clip.hardEdge,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header image + title
             Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ClipRect(
                    child: Align(
                      alignment: Alignment.bottomCenter,
                      heightFactor: 0.9, // crops top 10%
                      child: Image.asset(
                        'assets/media/pngs/success_slip.png',
                        width: double.infinity,
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                    color: Colors.transparent, // transparent background
                    child: const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Bet Placed',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 17,
                            fontWeight: FontWeight.bold,
                            shadows: [Shadow(color: Colors.black, blurRadius: 4)],
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Your bet has been successfully placed. Good luck!',
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

              // Ticker with logo and symbol
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 5.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Ticker', style: TextStyle(color: Colors.white)),
                    Row(
                      children: [
                        CircleAvatar(
                          radius: 10,
                          backgroundImage: NetworkImage(logoUrl),
                          backgroundColor: Colors.transparent,
                        ),
                        const SizedBox(width: 6),
                        Text('\$$symbol', style: const TextStyle(color: Colors.white)),
                      ],
                    ),
                  ],
                ),
              ),

              infoRow('Exp Date', formatDateToNam(expDate)),
              infoRow('Odds', odds),
              infoRow('Wager Amount', wagerAmount),

              // Divider
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 5.0),
                child: Divider(color: Colors.grey.shade400, thickness: 1),
              ),
              Row(
                mainAxisSize: MainAxisSize.max,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 5.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: const [
                    Text(
                      'Potential Payout',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0),
                child: Align(
                  alignment: Alignment.centerRight,
                  child: Text(
                    payout,
                    style: const TextStyle(
                      color: Colors.greenAccent,
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
                ],
              ),
              // Payout
              

              const SizedBox(height: 10),

              // Button
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 5.0),
                child: CustomButton(
                  text: 'Go home',
                  onPressed: () {
                    Navigator.of(context, rootNavigator: true).pop(); // close dialog
                          // navigate
                  },
                ),
              ),

              const SizedBox(height: 10),
            ],
          ),
        ),
      ),
    );
  }

  Widget infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 5.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.white)),
          Text(value, style: const TextStyle(color: Colors.white)),
        ],
      ),
    );
  }
}

/// Helper to open the dialog correctly (outside-tap closes via route barrier).
Future<void> showSuccessDialog(BuildContext context, SuccessDialog dialog) {
  return showDialog(
    context: context,
    useRootNavigator: true,
    barrierDismissible: true,
    barrierColor: Colors.black54, // dim background
    builder: (_) => dialog,
  );
}
