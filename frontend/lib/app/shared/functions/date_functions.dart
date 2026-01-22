import 'package:frontend/app/shared/functions/string_functions.dart';

class Weekday {
  final int day;
  final int month;
  final int year;

  Weekday(this.day, this.month, this.year);

  @override
  String toString() {
    return 'Day: $day, Month: $month, Year: $year';
  }

  String getDay() {
    return "$day ${getMonth(month, capitalized: true)} $year";
  }
}

enum WeekdayState {
  free,
  booked,
  blocked,
}

final months = [
  "january",
  "february",
  "march",
  "april",
  "may",
  "june",
  "july",
  "august",
  "september",
  "october",
  "november",
  "december"
];

final shorts = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

String getMonth(int monthNumber,
    {bool capitalized = false, bool isShorts = false}) {
  if (isShorts) {
    return shorts[monthNumber - 1];
  }

  final full = months[monthNumber - 1];
  return capitalized ? capitalize(full) : full;
}

/// Extension for formatting DateTime to short date strings.
extension DateFormatting on DateTime {
  /// e.g. DateTime(2025,6,14).toShortDate() => "Jun 14, 2025"
  String toShortDate() {
    final m = shorts[month - 1];
    return '$m $day, $year';
  }
}

/// Extension for parsing ISO date strings (yyyy-MM-dd) to short date.
extension StringDateFormatting on String {
  /// Parses an ISO‑8601 date (yyyy-MM-dd) and formats it
  /// e.g. "2025-06-14".toShortDate() => "Jun 14, 2025"
  String toShortDate() {
    final dt = DateTime.parse(this);
    return dt.toShortDate();
  }
}

String formatDateTimeToMMDDYYYY(DateTime dateTime) {
  return "${getMonth(dateTime.month, capitalized: true, isShorts: true)} ${dateTime.day}, ${dateTime.year}";
}

String formatDateTime(DateTime dateTime) {
  return "${dateTime.day} ${getMonth(dateTime.month, capitalized: true)} ${dateTime.year}";
}

bool sameDate(DateTime date1, DateTime date2) {
  return date1.day == date2.day &&
      date1.month == date2.month &&
      date1.year == date2.year;
}

DateTime toDateTime(String date) {
  final parts = date.split("-");
  return DateTime(
      int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
}

String doubleHourToWords(double theHours) {
  final hours = theHours.floor();
  final minutes = ((theHours - hours) * 60).floor();
  if (hours == 0) {
    return numberSuffixWord(minutes, "minute");
  }
  if (minutes == 0) {
    return numberSuffixWord(hours, "hour");
  }
  return "${numberSuffixWord(hours, "hour")}, ${numberSuffixWord(minutes, "minute")}";
}

DateTime justDate(DateTime dateTime) {
  return DateTime(dateTime.year, dateTime.month, dateTime.day);
}

String formatDateTimeToDDMMYYYYHHmm(DateTime dateTime) {
  final day = dateTime.day.toString().padLeft(2, '0');
  final month = dateTime.month.toString().padLeft(2, '0');
  final year = dateTime.year;
  final hour = dateTime.hour.toString().padLeft(2, '0');
  final minute = dateTime.minute.toString().padLeft(2, '0');
  return "$day/$month/$year, $hour:$minute";
}
