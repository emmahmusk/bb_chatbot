import 'dart:io';
import 'dart:typed_data';

Future<Uint8List> fileToBytes(String filePath) async {
  File file = File(filePath);
  Uint8List fileBytes = await file.readAsBytes();
  return fileBytes;
}
