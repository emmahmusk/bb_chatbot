import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/classes/fonts/fonts.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/classes/media/svgs.dart';
import 'package:frontend/app/shared/presentation/widgets/close_icon.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';

class AuthDialog extends ConsumerWidget {
  const AuthDialog({super.key, required this.child, this.height = 526});
  final Widget child;
  final double? height;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Container(
      width: 490,
      height: height,
      padding: const EdgeInsets.all(24),
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
          const SizedBox(height: 44),
          Expanded(
            child: SingleChildScrollView(
              child: child,
            ),
          ),
        ],
      ),
    );
  }
}
