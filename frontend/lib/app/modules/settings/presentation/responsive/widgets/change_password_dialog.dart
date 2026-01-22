import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/classes/fonts/fonts.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/classes/media/svgs.dart';
import 'package:frontend/app/shared/presentation/widgets/close_icon.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';

class ChangePasswordDialog extends ConsumerStatefulWidget {
  const ChangePasswordDialog({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _ChangePasswordDialogState();
}

class _ChangePasswordDialogState extends ConsumerState<ChangePasswordDialog> {
  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    return Container(
      width: 490,
      height: 312,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: colors.always161B22,
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
          Center(
            child: Text(
              'Change password',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w600,
                color: colors.alwaysWhite,
              ),
            ),
          ),
          const SizedBox(height: 12),
          RichText(
            textAlign: TextAlign.center,
            text: TextSpan(
              style: TextStyle(
                color: colors.always8B949E,
                fontSize: 16,
              ),
              children: [
                TextSpan(text: 'An email will be sent to '),
                TextSpan(
                  text: 'jane.doe@email.com',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: colors.alwaysWhite,
                  ),
                ),
                TextSpan(text: ' containing\npassword reset instructions.'),
              ],
            ),
          ),
          const SizedBox(height: 44),
          CustomButton(
            text: 'Send reset password email',
            validator: () => false,
            onPressed: () {},
          ),
        ],
      ),
    );
  }
}
