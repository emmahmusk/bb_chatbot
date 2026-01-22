extension StringExtension on String {
  /// Returns true if this string matches a basic email pattern.
  bool isValidEmail() {
    final emailRegExp = RegExp(
      r"^[a-zA-Z0-9.a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+"
      r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
      r"(?:\.[a-zA-Z]{2,})+$",
    );
    return emailRegExp.hasMatch(trim());
  }

  /// Returns true if the string is not empty and has more than 5 characters.
  bool get isNotEmptyAndLongerThan5 {
    return trim().isNotEmpty && length > 5;
  }
}
