import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class CustomButton extends ConsumerWidget {
  final String text;
  final VoidCallback? onPressed;
  final Widget? icon;
  final Color? color;
  final List<Color>? gradientColors;
  final bool Function()? validator;
  final MainAxisAlignment mainAxisAlignment;
  final EdgeInsets? padding;
  final double? width;
  final double? height;
  final double borderRadius;
  final double fontSize;
  final TextStyle? textStyle;

  const CustomButton({
    super.key,
    required this.text,
    this.onPressed,
    this.icon,
    this.color,
    this.gradientColors,
    this.validator,
    this.mainAxisAlignment = MainAxisAlignment.center,
    this.padding,
    this.width = double.maxFinite,
    this.height,
    this.borderRadius = 12.0,
    this.fontSize = 20.0,
    this.textStyle,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    final isValid = validator == null || validator!();

    final backgroundColor = isValid ? null : colors.always2D333B;

    final fgColor = isValid
        ? (textStyle?.color ?? colors.alwaysWhite)
        : colors.always6E7681;

    final effectiveGradient = isValid
        ? (gradientColors ?? [colors.always2867DF, colors.alwaysE954F6])
        : null;

    return Clickable(
      onClick: isValid ? onPressed : null,
      child: Stack(
        children: [
          if (isValid && effectiveGradient != null)
            Positioned.fill(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(borderRadius),
                child: BackdropFilter(
                  filter: ImageFilter.blur(
                    sigmaX: 0,
                    sigmaY: 0,
                  ),
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: effectiveGradient,
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          Container(
            width: width,
            height: height,
            decoration: BoxDecoration(
              color: isValid
                  ? (effectiveGradient == null
                      ? (color ?? colors.primary)
                      : null)
                  : backgroundColor,
              gradient: isValid && effectiveGradient != null
                  ? LinearGradient(
                      colors: effectiveGradient,
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    )
                  : null,
              borderRadius: BorderRadius.circular(borderRadius),
              boxShadow: isValid && effectiveGradient != null
                  ? [
                      BoxShadow(
                        color: effectiveGradient.first.withOpacity(0.3),
                        offset: const Offset(0, 4),
                        blurRadius: 12,
                      ),
                    ]
                  : null,
            ),
            padding: padding ??
                const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 14,
                ),
            child: Material(
              color: Colors.transparent,
              borderRadius: BorderRadius.circular(borderRadius),
              child: Row(
                mainAxisAlignment: mainAxisAlignment,
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (icon != null) ...[
                    icon!,
                    const SizedBox(width: 8),
                  ],
                  Text(
                    text,
                    style: textStyle ??
                        TextStyle(
                          color: fgColor,
                          fontSize: fontSize,
                          fontWeight: FontWeight.w500,
                        ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

enum IconPosition {
  left,
  right,
}

class CustomOutlinedButtonWithIcon extends ConsumerWidget {
  final String text;
  final VoidCallback? onTap;
  final Widget? icon;
  final IconPosition iconPosition;
  final Color? color;
  final EdgeInsets? padding;
  final double fontSize;
  final FontWeight fontWeight;
  const CustomOutlinedButtonWithIcon({
    super.key,
    required this.text,
    this.onTap,
    this.icon,
    this.color,
    this.iconPosition = IconPosition.left,
    this.padding = const EdgeInsets.symmetric(
      horizontal: 18,
      vertical: 14,
    ),
    this.fontSize = 12,
    this.fontWeight = FontWeight.w500,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    final color = this.color ?? colors.always7F7F7F;
    return Clickable(
      onClick: onTap,
      child: Container(
        height: 48,
        padding: padding,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(50),
          border: Border.all(
            color: colors.always30363D,
          ),
          color: colors.always30363D.withValues(alpha: 0.2),
        ),
        child: Row(
          children: [
            if (icon != null && iconPosition == IconPosition.left) ...[
              icon!,
              const SizedBox(width: 8),
            ],
            Text(
              text,
              style: TextStyle(
                color: color,
                fontSize: fontSize,
                fontWeight: fontWeight,
              ),
            ),
            if (icon != null && iconPosition == IconPosition.right) ...[
              icon!,
              const SizedBox(width: 8),
            ],
          ],
        ),
      ),
    );
  }
}

class CustomOutlinedButton extends ConsumerWidget {
  final String text;
  final VoidCallback? onTap;
  final Widget? icon;
  final IconPosition iconPosition;
  final Color? color;
  final EdgeInsets? padding;
  final double? height;
  final bool isBig;
  final Color? textColor;
  final Color? borderColor;

  const CustomOutlinedButton({
    super.key,
    required this.text,
    this.onTap,
    this.icon,
    this.color,
    this.iconPosition = IconPosition.left,
    this.padding,
    this.height,
    this.isBig = false,
    this.textColor,
    this.borderColor,
  });

  factory CustomOutlinedButton.big({
    required String text,
    VoidCallback? onTap,
    Widget? icon,
    Color? color,
    IconPosition iconPosition = IconPosition.left,
    EdgeInsets? padding,
    Color? textColor,
    Color? borderColor,
  }) {
    return CustomOutlinedButton(
      text: text,
      onTap: onTap,
      icon: icon,
      color: color,
      iconPosition: iconPosition,
      padding: padding,
      height: 48,
      isBig: true,
      textColor: textColor,
      borderColor: borderColor,
    );
  }

  factory CustomOutlinedButton.small({
    required String text,
    VoidCallback? onTap,
    Widget? icon,
    Color? color,
    IconPosition iconPosition = IconPosition.left,
    EdgeInsets? padding,
    Color? textColor,
    Color? borderColor,
  }) {
    return CustomOutlinedButton(
      text: text,
      onTap: onTap,
      icon: icon,
      color: color,
      iconPosition: iconPosition,
      padding: padding,
      height: 36,
      isBig: false,
      textColor: textColor,
      borderColor: borderColor,
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    final color = this.color ?? colors.always30363D.withValues(alpha: 0.2);
    final textColor = this.textColor ?? colors.alwaysWhite;
    final borderColor = this.borderColor ?? colors.always30363D;
    EdgeInsets? padding = this.padding;
    if (isBig) {
      padding = const EdgeInsets.symmetric(
        horizontal: 18,
        vertical: 14,
      );
    }
    return Clickable(
      onClick: onTap,
      child: Container(
        height: height,
        padding: padding ??
            const EdgeInsets.symmetric(
              horizontal: 18,
            ),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(50),
          border: Border.all(
            color: borderColor,
          ),
          color: color,
        ),
        child: Center(
          child: Text(
            text,
            style: TextStyle(
              color: textColor,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}

