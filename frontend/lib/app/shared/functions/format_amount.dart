import 'package:intl/intl.dart';

String formatAmount(num value, {int decimalDigits = 2}) {
  final formatter = NumberFormat.decimalPattern();
  if (value is int) {
    return formatter.format(value);
  } else {
    return formatter.format(value) + (decimalDigits > 0 ? value.toStringAsFixed(decimalDigits).substring(value.toStringAsFixed(decimalDigits).indexOf('.')) : '');
  }
}
