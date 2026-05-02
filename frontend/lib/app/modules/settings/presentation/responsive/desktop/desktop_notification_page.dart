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

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
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
          _PreferenceRow(
            title: 'Account updates',
            description: 'Service upgrades, market holidays and new features.',
            value: accountUpdates,
            onTap: () {
              setState(() => accountUpdates = !accountUpdates);
            },
          ),
          const SizedBox(height: 28),
          _PreferenceRow(
            title: 'Bet updates',
            description: 'Service upgrades, market holidays and new features.',
            value: betUpdates,
            onTap: () {
              setState(() => betUpdates = !betUpdates);
            },
          ),
          const SizedBox(height: 28),
          _PreferenceRow(
            title: 'Product & feature updates',
            description:
                'News about our latest work, product updates, quality of life changes and tips about using BullBear.',
            value: productUpdates,
            onTap: () {
              setState(() => productUpdates = !productUpdates);
            },
          ),
        ],
      ),
    );
  }
}

class _PreferenceRow extends ConsumerWidget {
  const _PreferenceRow({
    required this.title,
    required this.description,
    required this.value,
    required this.onTap,
  });

  final String title;
  final String description;
  final bool value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: colors.alwaysWhite,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
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
          child: CustomCheckbox(value: value, onTap: onTap),
        ),
      ],
    );
  }
}
