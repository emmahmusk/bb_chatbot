import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/settings/presentation/responsive/widgets/transaction_details_dialog.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/functions/date_functions.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'package:frontend/app/shared/presentation/widgets/custom_textfield.dart';
import 'dart:convert';
import 'package:frontend/app/shared/classes/preferences/preferences.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';

class DesktopWalletTransactionsPage extends ConsumerStatefulWidget {
  const DesktopWalletTransactionsPage({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _DesktopWalletTransactionsPageState();
}

class _DesktopWalletTransactionsPageState
    extends ConsumerState<DesktopWalletTransactionsPage> {
  double walletBalance = 0.0;
  double walletCoinBalance = 0.0;
  List<dynamic> transactions = [];
  List<dynamic> conversionTable = [];
  bool isLoading = true;

  int currentPage = 1;
  String? nextUrl;
  String? prevUrl;
  int? totalCount;

  @override
  void initState() {
    super.initState();
    fetchConversionTable();
    fetchWalletHistory(); // page = currentPage (1)
  }

  Future<void> fetchConversionTable() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('access_token');

      final res = await http.get(
        Uri.parse(
            "https://api.bbbprediction.com/users/wallet/coins/conversion-table/"),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
      );

      if (res.statusCode == 200) {
        final data = json.decode(res.body) as Map<String, dynamic>;
        setState(() {
          conversionTable = List<dynamic>.from(data['conversion_table'] ?? []);
        });
      }
    } catch (_) {}
  }

  Future<void> fetchWalletHistory({int? page}) async {
    final targetPage = page ?? currentPage;

    setState(() {
      isLoading = true;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('access_token');

      final uri = Uri.parse(
          "https://api.bbbprediction.com/users/wallet/history/?page=$targetPage");
      final res = await http.get(
        uri,
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
      );

      if (res.statusCode == 200) {
        final data = json.decode(res.body) as Map<String, dynamic>;
        print("Wallet response: $data");

        final results = data['results'] as Map<String, dynamic>? ?? {};
        final transactionsList =
            List<dynamic>.from(results["transactions"] ?? []);

        final walletBalanceRaw = results["wallet_balance"];
        final walletBalanceDouble = (walletBalanceRaw is num)
            ? walletBalanceRaw.toDouble()
            : double.tryParse(walletBalanceRaw?.toString() ?? '') ?? 0.0;
        final walletCoinBalanceRaw = results["wallet_coin_balance"];
        final walletCoinBalanceDouble = (walletCoinBalanceRaw is num)
          ? walletCoinBalanceRaw.toDouble()
          : double.tryParse(walletCoinBalanceRaw?.toString() ?? '') ?? 0.0;

        // Update Riverpod user profile
        final currentUser = ref.read(currentUserProvider);
        if (currentUser != null) {
          final updatedUser = Profile(
            id: currentUser.id,
            user: currentUser.user,
            emailVerified: currentUser.emailVerified,
            fullName: currentUser.fullName,
            email: currentUser.email,
            dateOfBirth: currentUser.dateOfBirth,
            phoneNumber: currentUser.phoneNumber,
            physicalAddress: currentUser.physicalAddress,
            walletBalance: walletBalanceDouble.toString(),
          );

          ref.read(currentUserProvider.notifier).state = updatedUser;
        }

        setState(() {
          currentPage = targetPage;
          walletBalance = walletBalanceDouble;
          walletCoinBalance = walletCoinBalanceDouble;
          transactions = transactionsList;
          totalCount = data['count'] as int?;
          nextUrl = data['next'] as String?;
          prevUrl = data['previous'] as String?;
          isLoading = false;
        });

        // Save latest balance in prefs
        prefs.setString('wallet_balance', walletBalanceDouble.toString());
      } else {
        print("Failed with status: ${res.statusCode}");
        setState(() => isLoading = false);
      }
    } catch (e) {
      print("Error fetching wallet: $e");
      setState(() => isLoading = false);
    }
  }

  void showConvertCoinsDialog() {
    String coinsAmount = '';
    final colors = ref.watch(appThemeProvider).colors;

    showDialog(
      context: context,
      builder: (_) {
        return AlertDialog(
          backgroundColor: const Color(0xFF0D1117),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          contentPadding: const EdgeInsets.all(24),
          content: SizedBox(
            width: 420,
            child: StatefulBuilder(
              builder: (context, setState) {
                return Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: Text(
                        'Convert BullBear Coins',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: colors.alwaysWhite,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Available: ${walletCoinBalance.toStringAsFixed(2)} BBC',
                      style: TextStyle(
                        fontSize: 12,
                        color: colors.always8B949E,
                      ),
                    ),
                    const SizedBox(height: 16),
                    CustomTextField(
                      headerText: 'Coins Amount',
                      hint: 'Enter coin amount',
                      onChanged: (val) => setState(() => coinsAmount = val),
                    ),
                    if (conversionTable.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Text(
                        'Reward Conversion Table',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: colors.alwaysWhite,
                        ),
                      ),
                      const SizedBox(height: 6),
                      ...conversionTable.take(3).map((row) {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text(
                            '${row['tier']}: \$${row['min_cash']} - \$${row['max_cash']} => ${row['coins_per_dollar']} BBC / \$1',
                            style: TextStyle(
                              fontSize: 11,
                              color: colors.always8B949E,
                            ),
                          ),
                        );
                      }).toList(),
                    ],
                    const SizedBox(height: 20),
                    CustomButton(
                      text: 'Convert to Cash',
                      onPressed: () async {
                        if (coinsAmount.isEmpty) return;

                        final prefs = await SharedPreferences.getInstance();
                        final token = prefs.getString('access_token');

                        final res = await http.post(
                          Uri.parse(
                              'https://api.bbbprediction.com/users/wallet/coins/convert-to-cash/'),
                          headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer $token',
                          },
                          body: jsonEncode({
                            'coins_amount': coinsAmount,
                            'description': 'Wallet coin redemption',
                          }),
                        );

                        if (res.statusCode == 200 || res.statusCode == 201) {
                          await fetchWalletHistory();
                          Navigator.pop(context);
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Coins converted successfully.'),
                              ),
                            );
                          }
                          return;
                        }

                        String errorMessage = 'Conversion failed.';
                        try {
                          final responseBody = jsonDecode(res.body) as dynamic;
                          if (responseBody is Map &&
                              responseBody['detail'] != null) {
                            errorMessage = responseBody['detail'].toString();
                          }
                        } catch (_) {}

                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text(errorMessage)),
                          );
                        }
                      },
                      validator: () => coinsAmount.isNotEmpty,
                    ),
                  ],
                );
              },
            ),
          ),
        );
      },
    );
  }

  void showWalletActionDialog(String heading) {
    String amount = '';
    String description = '';
    final colors = ref.watch(appThemeProvider).colors;

    showDialog(
      context: context,
      builder: (_) {
        return AlertDialog(
          backgroundColor: const Color(0xFF0D1117), // Dark background
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          contentPadding: const EdgeInsets.all(24),
          content: SizedBox(
            width: 400,
            child: StatefulBuilder(
              builder: (context, setState) {
                return Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: Text(
                        heading,
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: colors.alwaysWhite,
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),

                    /// Amount field
                    CustomTextField(
                      headerText: 'Amount',
                      hint: 'Enter amount',
                      onChanged: (val) => setState(() => amount = val),
                    ),
                    const SizedBox(height: 16),

                    /// Description field
                    CustomTextField(
                      headerText: 'Description',
                      hint: 'Reason or Notes',
                      onChanged: (val) => setState(() => description = val),
                    ),
                    const SizedBox(height: 24),

                    /// Submit button
                    CustomButton(
                      text: 'Submit',
                      onPressed: () async {
                        if (amount.isEmpty || description.isEmpty) return;

                        final prefs = await SharedPreferences.getInstance();
                        final token = prefs.getString('access_token');

                        final isWithdraw = heading == 'Withdraw Wallet' ||
                            heading == 'Withdraw'; // optional flexibility
                        final url = isWithdraw
                            ? 'https://api.bbbprediction.com/users/wallet/withdraw/'
                            : 'https://api.bbbprediction.com/users/wallet/fund/';

                        try {
                          final res = await http.post(
                            Uri.parse(url),
                            headers: {
                              'Content-Type': 'application/json',
                              'Authorization': 'Bearer $token',
                            },
                            body: jsonEncode({
                              'amount': amount,
                              'description': description,
                            }),
                          );

                          if (res.statusCode == 200) {
                            await fetchWalletHistory(); // Refresh wallet data, stays on current page
                            Navigator.pop(context);
                          } else {
                            // Only show error for withdraw API
                            if (isWithdraw) {
                              String errorMessage = 'Something went wrong.';
                              try {
                                final responseBody =
                                    jsonDecode(res.body) as dynamic;
                                if (responseBody is Map &&
                                    responseBody['error'] != null) {
                                  errorMessage = responseBody['error'];
                                } else if (responseBody is Map &&
                                    responseBody['message'] != null) {
                                  errorMessage = responseBody['message'];
                                }
                              } catch (_) {
                                // Ignore parse error and use default message
                              }

                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text(errorMessage)),
                              );
                            }

                            await fetchWalletHistory();
                            Navigator.pop(context);
                          }
                        } catch (e) {
                          if (isWithdraw) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                  content: Text(
                                      'Network error: ${e.toString()}')),
                            );
                          }

                          await fetchWalletHistory();
                          Navigator.pop(context);
                        }
                      },
                      validator: () =>
                          amount.isNotEmpty && description.isNotEmpty,
                    ),
                  ],
                );
              },
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;

    if (isLoading) {
      return const Center(
        child: SizedBox(
          width: 40,
          height: 40,
          child: CircularProgressIndicator(color: Color(0xFFFFFFFF)),
        ),
      );
    }

    final canGoPrev = prevUrl != null && currentPage > 1;
    final canGoNext = nextUrl != null;

    return ListView(
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Text(
              'Wallet & Transactions',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w600,
                color: colors.alwaysWhite,
              ),
            ),
            const SizedBox(height: 32),

            // Balance + buttons
            Row(
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Wallet balance',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w400,
                        color: colors.always8B949E,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '\$${walletBalance.toStringAsFixed(2)}',
                      style: TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.w600,
                        color: colors.alwaysWhite,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '${walletCoinBalance.toStringAsFixed(2)} BBC',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                        color: colors.alwaysFFD33D,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                CustomOutlinedButtonWithIcon(
                  icon: Image.asset(Pngs.plus, width: 16, height: 16),
                  text: 'Fund Wallet',
                  color: colors.alwaysWhite,
                  onTap: () => showWalletActionDialog("Fund Wallet"),
                ),
                const SizedBox(width: 16),
                CustomOutlinedButtonWithIcon(
                  icon:
                      Image.asset(Pngs.arrowUpRight, width: 16, height: 16),
                  text: 'Withdraw',
                  color: colors.alwaysWhite,
                  onTap: () => showWalletActionDialog("Withdraw"),
                ),
                const SizedBox(width: 16),
                CustomOutlinedButtonWithIcon(
                  icon: Image.asset(Pngs.wallet, width: 16, height: 16),
                  text: 'Convert Coins',
                  color: colors.alwaysWhite,
                  onTap: showConvertCoinsDialog,
                ),
              ],
            ),

            const SizedBox(height: 44),

            // Recent Transactions label
            Text(
              'Recent Transactions',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: colors.always8B949E,
              ),
            ),
            const SizedBox(height: 12),
            const CustomDivider(),
            const SizedBox(height: 30),

            // Transactions list
            if (transactions.isEmpty)
              Text(
                'No transactions found.',
                style: TextStyle(color: colors.always8B949E),
              )
            else ...[
              ...transactions.map((txn) {
                final isCredit = txn['transaction_type'] == 'credit';
                final sign = isCredit ? '+' : '-';
                final priceColor =
                    isCredit ? colors.always27D07F : colors.alwaysFFD33D;
                final icon =
                    isCredit ? Pngs.walletDeposit : Pngs.bankWithdrawal;
                final dt = DateTime.parse(txn['created_at']);

                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: WalletTransactionsItem(
                    asset: icon,
                    date: dt,
                    price: txn['amount'].toString(),
                    transaction: txn['description'] ?? "Transaction",
                    sign: sign,
                    priceColor: priceColor,
                    onClick: () {
                      showCenterDialog(
                        context,
                        child: const TransactionDetailsDialog(),
                      );
                    },
                  ),
                );
              }).toList(),

              const SizedBox(height: 16),

              // Pagination controls with CustomOutlinedButtonWithIcon
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  if (totalCount != null)
                    Text(
                      'Total: $totalCount transactions',
                      style: TextStyle(
                        fontSize: 12,
                        color: colors.always8B949E,
                      ),
                    )
                  else
                    const SizedBox.shrink(),
                  Row(
                    children: [
                      Opacity(
                        opacity: canGoPrev ? 1.0 : 0.4,
                        child: CustomOutlinedButtonWithIcon(
                          icon: Icon(
                            Icons.arrow_back_ios_new,
                            size: 14,
                            color: colors.alwaysWhite,
                          ),
                          text: 'Previous',
                          color: colors.alwaysWhite,
                          onTap: () {
                            if (!canGoPrev) return;
                            fetchWalletHistory(page: currentPage - 1);
                          },
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Page $currentPage',
                        style: TextStyle(
                          fontSize: 12,
                          color: colors.always8B949E,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Opacity(
                        opacity: canGoNext ? 1.0 : 0.4,
                        child: CustomOutlinedButtonWithIcon(
                          icon: Icon(
                            Icons.arrow_forward_ios,
                            size: 14,
                            color: colors.alwaysWhite,
                          ),
                          text: 'Next',
                          color: colors.alwaysWhite,
                          onTap: () {
                            if (!canGoNext) return;
                            fetchWalletHistory(page: currentPage + 1);
                          },
                        ),
                      ),
                    ],
                  ),
                 
                ],
              ),
               SizedBox(height:100)
            ],
          ],
        ),
      ],
    );
  }
}

class WalletTransactionsItem extends ConsumerWidget {
  const WalletTransactionsItem({
    super.key,
    required this.asset,
    required this.date,
    required this.price,
    required this.transaction,
    required this.onClick,
    this.subtitle,
    this.priceColor,
    this.sign = "-",
  });

  final String asset;
  final String transaction;
  final DateTime date;
  final String price;
  final String? subtitle;
  final Color? priceColor;
  final String sign;
  final VoidCallback onClick;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Clickable(
      onClick: onClick,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        child: Row(
          children: [
            Image.asset(asset, width: 40, height: 40),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  transaction,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: colors.alwaysWhite,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle!,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w400,
                      color: colors.always8B949E,
                    ),
                  ),
                ],
              ],
            ),
            const Spacer(),
            Text(
              formatDateTimeToDDMMYYYYHHmm(date),
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: colors.alwaysWhite,
              ),
            ),
            const SizedBox(width: 40),
            Text(
              '$sign\$$price',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: priceColor ?? colors.always27D07F,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
