import 'package:intl/intl.dart';

String formatAmount(num value, {int decimalDigits = 2}) {
  final formatter = NumberFormat.currency(
    symbol: '',
    decimalDigits: decimalDigits,
    customPattern: '#,##0.00',
  );
  return formatter.format(value).trim();
}
