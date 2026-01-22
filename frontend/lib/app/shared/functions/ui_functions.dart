import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:frontend/app/shared/functions/string_functions.dart';

double getTextWidth(String text, TextStyle style) {
  final textPainter = TextPainter(
    text: TextSpan(text: text, style: style),
    maxLines: 1,
    textDirection: TextDirection.ltr,
  )..layout(minWidth: 0, maxWidth: double.infinity);

  return textPainter.width;
}

void hideKeyBoard() {
  SystemChannels.textInput.invokeMethod('TextInput.hide');
}

String? emailValidator(value) {
  return isValidEmailAddress(value) ? null : "Invalid email";
}