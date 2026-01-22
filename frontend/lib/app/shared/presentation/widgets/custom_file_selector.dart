import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/functions/file_functions.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class CustomFileSelector extends ConsumerWidget {
  final ExistingFile? existingFile;
  final ValueChanged<ExistingFile?> onFileSelected;
  final double size;
  final Color? backgroundColor;
  final Color? borderColor;
  final bool showPickerButton;

  const CustomFileSelector({
    super.key,
    this.existingFile,
    required this.onFileSelected,
    this.size = 120.0,
    this.backgroundColor,
    this.borderColor,
    this.showPickerButton = true,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          // Main circular avatar
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: borderColor != null
                  ? null
                  : const LinearGradient(
                      colors: [
                        Color(0xFF6366F1), // Indigo
                        Color(0xFFA855F7), // Purple
                        Color(0xFFEC4899), // Pink
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
              color: borderColor,
              border: borderColor != null
                  ? Border.all(color: borderColor!, width: 2)
                  : null,
            ),
            child: Padding(
              padding: const EdgeInsets.all(4.0),
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: backgroundColor ?? colors.primary,
                ),
                child: ClipOval(
                  child: existingFile?.bytes != null
                      ? Image.memory(
                          existingFile!.bytes!,
                          fit: BoxFit.cover,
                          width: size - 8,
                          height: size - 8,
                        )
                      : Container(
                          width: size - 8,
                          height: size - 8,
                          color: backgroundColor ?? colors.primary,
                          child: Icon(
                            Icons.person,
                            size: size * 0.4,
                            color: colors.primary.withOpacity(0.6),
                          ),
                        ),
                ),
              ),
            ),
          ),

          // Camera icon overlay
          if (showPickerButton)
            Positioned(
              bottom: 0,
              right: 0,
              child: GestureDetector(
                onTap: () async {
                  final pickedFile = await FilePicker.platform.pickFiles(
                    type: FileType.image,
                  );

                  if (pickedFile != null) {
                    final file = pickedFile.files.first;
                    Uint8List? bytes = file.bytes;
                    bytes ??= await fileToBytes(file.path!);
                    final fileName = file.name;

                    final existingFile = ExistingFile.fromBytes(
                      bytes: bytes,
                      fileName: fileName,
                    );
                    onFileSelected(existingFile);
                  }
                },
                child: Container(
                  width: size * 0.25,
                  height: size * 0.25,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                    border: Border.all(
                      color: Colors.grey[300]!,
                      width: 1,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.1),
                        blurRadius: 4,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Icon(
                    Icons.camera_alt,
                    size: size * 0.12,
                    color: Colors.grey[600],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class ExistingFile {
  final Uint8List? bytes;
  final String fileName;
  bool get isDownloadable => url.isNotEmpty;
  final String url;

  String get extension => fileName.split('.').last;

  ExistingFile({
    this.bytes,
    required this.fileName,
    required this.url,
  });

  factory ExistingFile.fromBytesAndUrl({
    required Uint8List bytes,
    required String fileName,
    required String url,
  }) {
    return ExistingFile(
      bytes: bytes,
      fileName: fileName,
      url: url,
    );
  }

  factory ExistingFile.fromUrl({
    required String fileName,
    required String url,
  }) {
    return ExistingFile(
      fileName: fileName,
      url: url,
    );
  }

  factory ExistingFile.fromBytes({
    required Uint8List bytes,
    required String fileName,
  }) {
    return ExistingFile(
      bytes: bytes,
      fileName: fileName,
      url: "",
    );
  }

  Uint8List get sureBytes => bytes!;
}
