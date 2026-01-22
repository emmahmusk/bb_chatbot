import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/settings/presentation/responsive/widgets/change_password_dialog.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class DesktopSecurityPage extends ConsumerStatefulWidget {
  const DesktopSecurityPage({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _DesktopSecurityPageState();
}

class _DesktopSecurityPageState extends ConsumerState<DesktopSecurityPage> {
  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Security',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: colors.alwaysWhite,
          ),
        ),
        const SizedBox(height: 44),
        Text(
          'Authentication details',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w400,
            color: colors.always8B949E,
          ),
        ),
        const SizedBox(height: 12),
        CustomDivider(),
        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'User name',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w400,
                      color: colors.always8B949E,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Janny78',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w400,
                      color: colors.always8B949E,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Icon(
              Icons.arrow_forward,
              size: 14,
              color: colors.always8B949E,
            ),
          ],
        ),
        const SizedBox(height: 32),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Clickable(
              onClick: () {
                showCenterDialog(context, child: ChangePasswordDialog());
              },
              child: Row(
                children: [
                  Image.asset(
                    Pngs.lock,
                    width: 20,
                    height: 20,
                    fit: BoxFit.cover,
                  ),
                  const SizedBox(width: 12),
                  Text(
                    'Change password',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w400,
                      color: colors.alwaysWhite,
                    ),
                  ),
                ],
              ),
            ),
            const Spacer(),
            Clickable(
              onClick: () {
                showCenterDialog(context, child: ChangePasswordDialog());
              },
              child: Icon(
                Icons.arrow_forward,
                size: 14,
                color: colors.always8B949E,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
