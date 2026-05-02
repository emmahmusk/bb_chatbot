import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/classes/fonts/fonts.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/classes/media/svgs.dart';
import 'package:frontend/app/shared/presentation/widgets/close_icon.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';

class AuthDialog extends ConsumerStatefulWidget {
  const AuthDialog({super.key, required this.child, this.height = 620});
  final Widget child;
  final double? height;

  @override
  ConsumerState<AuthDialog> createState() => _AuthDialogState();
}

class _AuthDialogState extends ConsumerState<AuthDialog> {
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final viewportHeight = MediaQuery.of(context).size.height;
    final viewportWidth = MediaQuery.of(context).size.width;
    final isCompact = viewportWidth < 900;
    final double effectiveHeight = math.min(
      widget.height ?? 620,
      math.max(520.0, viewportHeight - 32),
    );
    final double effectiveWidth = math.min(
      isCompact ? 560.0 : 490.0,
      math.max(320.0, viewportWidth - (isCompact ? 24 : 0)),
    );

    return Container(
      width: effectiveWidth,
      height: effectiveHeight,
      padding: EdgeInsets.all(isCompact ? 20 : 24),
      decoration: BoxDecoration(
        color: colors.primary,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: colors.always30363D.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              Container(),
              const Spacer(),
              Image.asset(
                Pngs.bullbearLogo,
                width: 63,
                height: 30,
                fit: BoxFit.cover,
              ),
              const SizedBox(width: 6.51),
              Text(
                'BULL BEAR',
                style: TextStyle(
                  fontFamily: Fonts.bigShoulders,
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: colors.alwaysWhite,
                ),
              ),
              const Spacer(),
              CloseIcon(
                svg: Svgs.close,
                onTap: () => pop(context),
              ),
            ],
          ),
          SizedBox(height: isCompact ? 24 : 36),
          Expanded(
            child: ScrollbarTheme(
              data: ScrollbarThemeData(
                thumbColor: WidgetStatePropertyAll(
                  colors.alwaysWhite.withValues(alpha: 0.45),
                ),
                trackColor: WidgetStatePropertyAll(
                  colors.always30363D.withValues(alpha: 0.3),
                ),
                trackBorderColor:
                    const WidgetStatePropertyAll(Colors.transparent),
                radius: const Radius.circular(999),
                thickness: const WidgetStatePropertyAll(6),
                thumbVisibility: const WidgetStatePropertyAll(true),
                trackVisibility: const WidgetStatePropertyAll(true),
              ),
              child: Scrollbar(
                controller: _scrollController,
                thumbVisibility: true,
                trackVisibility: true,
                child: SingleChildScrollView(
                  controller: _scrollController,
                  padding: const EdgeInsets.only(right: 8),
                  child: widget.child,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
