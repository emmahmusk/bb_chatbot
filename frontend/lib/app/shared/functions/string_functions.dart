bool isValidEmailAddress(String it) =>
    RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$').hasMatch(it);

String? isValidPassword(String it) {
  if (it.length < 8) {
    return "Password must be at least 8 characters long";
  }
  if (!RegExp(r'[A-Z]').hasMatch(it)) {
    return "Password must contain at least one uppercase letter";
  }
  if (!RegExp(r'[a-z]').hasMatch(it)) {
    return "Password must contain at least one lowercase letter";
  }
  if (!RegExp(r'[0-9]').hasMatch(it)) {
    return "Password must contain at least one number";
  }
  return null;
}

String formatAmount(double it, [int itAsFixed = 2]) =>
    it.toStringAsFixed(itAsFixed).replaceAllMapped(
          RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'),
          (Match m) => '${m[1]},',
        );
String zeroPrefixNumber(int number) => number < 10 ? "0$number" : "$number";

String numberSuffixWord(int number, String word) {
  if (word.endsWith('y')) {
    return "$number ${number > 1 ? "${word.substring(0, word.length - 1)}ies" : word}";
  }
  return "$number ${number > 1 ? "${word}s" : word}";
}

String capitalize(String it) => it.isEmpty
    ? it
    : it[0].toUpperCase() + it.substring(1, it.length).toLowerCase();

String take(String it, int length) =>
    it.length > length ? it.substring(0, length) : it;

String capitalizeEach(String it) => it.split(" ").map(capitalize).join(" ");

String? emailValidator(value) {
  return isValidEmailAddress(value) ? null : "Invalid email";
}
