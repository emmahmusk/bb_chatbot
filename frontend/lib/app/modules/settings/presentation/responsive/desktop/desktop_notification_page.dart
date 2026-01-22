import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_checkbox.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class DesktopNotificationPage extends ConsumerStatefulWidget {
  const DesktopNotificationPage({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _DesktopNotificationPageState();
}

class _DesktopNotificationPageState
    extends ConsumerState<DesktopNotificationPage> {
  bool allNotifications = false;
  bool accountUpdates = false;
  bool betUpdates = false;
  bool productUpdates = false;

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Notifications',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: colors.alwaysWhite,
          ),
        ),
        const SizedBox(height: 44),
        Row(
          children: [
            Expanded(
              child: Text(
                'Type',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w400,
                  color: colors.always8B949E,
                ),
              ),
            ),
            Text(
              'Email',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: colors.always8B949E,
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        const CustomDivider(),
        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              child: Text(
                'All notifications',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: colors.alwaysWhite,
                ),
              ),
            ),
            CustomCheckbox(
              value: allNotifications,
              onTap: () {
                setState(() => allNotifications = !allNotifications);
              },
            ),
          ],
        ),
        const SizedBox(height: 24),
        const CustomDivider(),
        const SizedBox(height: 24),
        Text(
          'Account activities',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: colors.always8B949E,
          ),
        ),
        const SizedBox(height: 20),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Account updates',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: colors.alwaysWhite,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Service upgrades, market holidays and new features.',
                    style: TextStyle(
                      fontSize: 14,
                      height: 1.5,
                      color: colors.always8B949E,
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: CustomCheckbox(
                value: accountUpdates,
                onTap: () {
                  setState(() => accountUpdates = !accountUpdates);
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 28),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Bet updates',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: colors.alwaysWhite,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Service upgrades, market holidays and new features.',
                    style: TextStyle(
                      fontSize: 14,
                      height: 1.5,
                      color: colors.always8B949E,
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: CustomCheckbox(
                value: betUpdates,
                onTap: () {
                  setState(() => betUpdates = !betUpdates);
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 28),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Product & feature updates',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: colors.alwaysWhite,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'News about our latest work, product updates, quality of life changes and tips about using BullBear.',
                    style: TextStyle(
                      fontSize: 14,
                      height: 1.5,
                      color: colors.always8B949E,
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: CustomCheckbox(
                value: productUpdates,
                onTap: () {
                  setState(() => productUpdates = !productUpdates);
                },
              ),
            ),
          ],
        ),
      ],
    );
  }
}
