import 'dart:typed_data';

extension ListExtension<T> on List<T> {
  List<(int, T)> enumerate() {
    return asMap().entries.map((e) => (e.key, e.value)).toList();
  }

  List<T> reverseIf(bool condition) {
    return condition ? reversed.toList() : this;
  }

  List<T> takeLast(int count) {
    return reversed.take(count).toList().reversed.toList();
  }

  bool none(bool Function(T) test) {
    return !any(test);
  }

  bool equals(List<T> other) {
    if (length != other.length) return false;
    for (var i = 0; i < length; i++) {
      if (this[i] != other[i]) return false;
    }
    return true;
  }
}

extension ListRecordExtension on List<({String key, Uint8List byte})> {
  List<({String key, Uint8List byte, String extension})> get pdfBytes {
    return map((e) => (key: e.key, byte: e.byte, extension: "pdf")).toList();
  }
}

extension ToTRecord on List<String> {
  List<(String text, String value)> toTRecord() {
    return map((e) => (e, e)).toList();
  }
}
