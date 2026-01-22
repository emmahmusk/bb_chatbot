import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/core/framework/theme/colors/app_colors.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class CustomTextField extends ConsumerStatefulWidget {
  final String? hint;
  final ValueChanged<String>? onChanged;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final bool? readOnly;
  final TextEditingController? textEditingController;
  final bool? obscureText;
  final Widget? prefix;
  final Widget? suffix;
  final FocusNode? node;
  final VoidCallback? onTap;
  final String? Function(String value)? validator;
  final EdgeInsets? padding;
  final int? maxLines;
  final int? minLines;
  final int? maxLength;
  final Color? textFieldColor;
  final bool? hasBorder;
  final String? headerText;
  final TextInputAction textInputAction;
  final bool isPassword;
  final String? whenValid;
  final ({String tipTitle, String tipText})? tipInfo;
  final bool required;
  final double borderRadius;
  final ValueChanged<String>? onSubmitted;
  final bool? hasPrefixSpace;
  final Color? borderColor;
  final Gradient? focusGradient;

  const CustomTextField({
    super.key,
    this.hint,
    this.onChanged,
    this.keyboardType,
    this.inputFormatters,
    this.readOnly,
    this.obscureText,
    this.textEditingController,
    this.prefix,
    this.suffix,
    this.node,
    this.validator,
    this.onTap,
    this.padding,
    this.minLines = 1,
    this.maxLines = 1,
    this.maxLength,
    this.headerText,
    this.textInputAction = TextInputAction.next,
    this.hasBorder = true,
    this.textFieldColor,
    this.borderColor,
    this.isPassword = false,
    this.whenValid,
    this.tipInfo,
    this.required = false,
    this.onSubmitted,
    this.borderRadius = 12,
    this.hasPrefixSpace,
    this.focusGradient,
  });

  @override
  ConsumerState<CustomTextField> createState() => _CustomTextFieldState();
}

class _CustomTextFieldState extends ConsumerState<CustomTextField> {
  late final FocusNode node;
  late final TextEditingController controller;

  @override
  void initState() {
    super.initState();

    // Initialize controller
    controller = widget.textEditingController ?? TextEditingController();

    // Initialize focus node
    node = widget.node ?? FocusNode();

    if (widget.isPassword) {
      obscureText = true;
    }

    node.addListener(() {
      if (mounted) {
        setState(() {
          isFocused = node.hasFocus;
        });
      }
    });
  }

  @override
  void dispose() {
    // Only dispose if we created them
    if (widget.node == null) {
      node.dispose();
    }
    if (widget.textEditingController == null) {
      controller.dispose();
    }
    super.dispose();
  }

  bool obscureText = false;
  bool hasEntered = false;
  bool isFocused = false;

  @override
  Widget build(BuildContext context) {
    const red = Colors.red;
    final colors = ref.watch(appThemeProvider).colors;
    final shouldShowGradientBorder = isFocused &&
        widget.hasBorder == true &&
        isValid &&
        !(widget.whenValid != null && hasEntered);

    BoxBorder getBorder() {
      if (!isValid) {
        return Border.all(
          color: red,
          width: 1,
        );
      } else if (widget.whenValid != null && hasEntered) {
        return Border.all(
          color: red,
          width: 1,
        );
      }

      return Border.all(
        color: widget.borderColor ?? colors.always30363D,
        width: 1,
      );
    }

    return GestureDetector(
      onTap: () {
        if (widget.onTap != null) {
          widget.onTap!();
        }
        // Only request focus if not already focused
        if (!node.hasFocus) {
          node.requestFocus();
        }
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.headerText != null) ...[
            Row(
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Text(
                        widget.headerText!,
                        style: TextStyle(
                          color: colors.alwaysWhite,
                          fontSize: 14,
                          fontWeight: FontWeight.w300,
                        ),
                      ),
                      if (widget.required) ...[
                        const SizedBox(width: 5),
                        const Text(
                          "*",
                          style: TextStyle(
                            color: red,
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
          ],
          Stack(
            children: [
              if (shouldShowGradientBorder)
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(widget.borderRadius),
                      gradient: widget.focusGradient ??
                          const LinearGradient(
                            colors: [Color(0xFF667EEA), Color(0xFF764BA2)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                    ),
                  ),
                ),
              Container(
                margin: shouldShowGradientBorder
                    ? const EdgeInsets.all(1.5)
                    : EdgeInsets.zero,
                child: _textField(colors, getBorder()),
              ),
            ],
          ),
          if (!isValid)
            Column(
              children: [
                const SizedBox(height: 8),
                Text(
                  widget.validator!(value)!,
                  style: const TextStyle(color: red, fontSize: 12),
                ),
              ],
            ),
          if (widget.whenValid != null && isValid && hasEntered)
            Column(
              children: [
                const SizedBox(height: 8),
                Text(
                  widget.whenValid!,
                  style: TextStyle(color: colors.always027A48, fontSize: 12),
                ),
              ],
            )
        ],
      ),
    );
  }

  // Get current value from controller
  String get value => controller.text;

  bool get isValid {
    if (widget.validator == null || !hasEntered) {
      return true;
    }
    return widget.validator!(value) == null;
  }

  Container _textField(AppColors colors, BoxBorder border) {
    return Container(
      padding: widget.padding ??
          const EdgeInsets.symmetric(
            horizontal: 18,
            vertical: 12,
          ),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(widget.borderRadius),
        border: widget.hasBorder == true ? border : null,
        color: widget.textFieldColor ?? colors.always1F242C,
      ),
      child: Row(
        children: [
          widget.prefix ?? const SizedBox(),
          if (widget.prefix != null && widget.hasPrefixSpace == true)
            const SizedBox(width: 8),
          Expanded(
            child: TextField(
              maxLines: widget.maxLines,
              maxLength: widget.maxLength,
              focusNode: node,
              minLines: widget.minLines,
              keyboardType: widget.keyboardType,
              cursorColor: colors.alwaysWhite,
              onTap: () {
                if (widget.onTap != null) {
                  widget.onTap!();
                }
                node.requestFocus();
              },
              onSubmitted: (v) {
                widget.onSubmitted?.call(v);
              },
              onChanged: (v) {
                final trimmedValue = v.trim();
                widget.onChanged?.call(trimmedValue);
                setState(() {
                  hasEntered = trimmedValue.isNotEmpty;
                });
              },
              obscureText: widget.obscureText ?? obscureText,
              controller: controller, // Use the properly managed controller
              readOnly: widget.readOnly ?? false,
              inputFormatters: widget.inputFormatters,
              style: TextStyle(
                color: colors.alwaysWhite,
                fontSize: 14,
              ),
              decoration: InputDecoration.collapsed(
                hintText: widget.hint,
                hintStyle: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w300,
                  color: colors.alwaysWhite.withValues(alpha: 0.4),
                ),
              ),
              textInputAction: widget.textInputAction,
            ),
          ),
          widget.suffix ?? const SizedBox(),
          if (widget.isPassword)
            GestureDetector(
              onTap: () {
                // Keep focus when toggling password visibility
                if (!node.hasFocus) {
                  node.requestFocus();
                }
                setState(() {
                  obscureText = !obscureText;
                });
              },
              child: Image.asset(
                obscureText ? Pngs.eyeClosed : Pngs.eye,
                height: 16,
                width: 16,
                fit: BoxFit.cover,
              ),
            ),
        ],
      ),
    );
  }
}
