DateTime usEasternNow([DateTime? now]) {
  final utcNow = (now ?? DateTime.now()).toUtc();
  final offsetHours = _isEasternDaylightSavingTime(utcNow) ? -4 : -5;
  return utcNow.add(Duration(hours: offsetHours));
}

bool isUsMarketOpenNow([DateTime? now]) {
  final eastern = usEasternNow(now);
  if (eastern.weekday >= DateTime.saturday) {
    return false;
  }

  final openingTime = DateTime(
    eastern.year,
    eastern.month,
    eastern.day,
    9,
    30,
  );
  final closingTime = DateTime(
    eastern.year,
    eastern.month,
    eastern.day,
    16,
  );

  return !eastern.isBefore(openingTime) && !eastern.isAfter(closingTime);
}

bool _isEasternDaylightSavingTime(DateTime utcNow) {
  final year = utcNow.year;
  final dstStart = _nthWeekdayOfMonthUtc(year, 3, DateTime.sunday, 2);
  final dstEnd = _nthWeekdayOfMonthUtc(year, 11, DateTime.sunday, 1);

  final dstStartUtc = DateTime.utc(year, 3, dstStart.day, 7);
  final dstEndUtc = DateTime.utc(year, 11, dstEnd.day, 6);

  return !utcNow.isBefore(dstStartUtc) && utcNow.isBefore(dstEndUtc);
}

DateTime _nthWeekdayOfMonthUtc(
  int year,
  int month,
  int weekday,
  int occurrence,
) {
  final firstDayOfMonth = DateTime.utc(year, month, 1);
  final daysUntilWeekday =
      (weekday - firstDayOfMonth.weekday + 7) % 7;

  return firstDayOfMonth.add(
    Duration(days: daysUntilWeekday + ((occurrence - 1) * 7)),
  );
}
