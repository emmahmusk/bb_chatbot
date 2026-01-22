import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/extensions/list_extension.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class TableHeader extends ConsumerWidget {
  final List<String> tabs;
  final bool isCurved;
  const TableHeader({
    super.key,
    required this.tabs,
    this.isCurved = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Container(
      padding: const EdgeInsets.symmetric(
        vertical: 13,
        horizontal: 24,
      ),
      decoration: BoxDecoration(
        color: colors.alwaysF7F7F7,
        borderRadius: isCurved
            ? const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
              )
            : null,
      ),
      child: Row(
        children: [
          for (final (i, tab) in tabs.enumerate())
            Expanded(
              child: Row(
                children: [
                  Text(
                    tab,
                    style: TextStyle(
                      fontSize: 12,
                      color: colors.always7F7F7F,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  if (i == 0) ...[
                    const SizedBox(width: 4),
                    Icon(
                      Icons.arrow_downward,
                      size: 16,
                      color: colors.always7F7F7F,
                    ),
                  ]
                ],
              ),
            ),
        ],
      ),
    );
  }
}
