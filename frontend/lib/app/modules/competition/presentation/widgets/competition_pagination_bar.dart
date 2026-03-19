import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class CompetitionPaginationBar extends ConsumerWidget {
  const CompetitionPaginationBar({
    super.key,
    required this.currentPage,
    required this.hasPrevious,
    required this.hasNext,
    required this.onPrevious,
    required this.onNext,
  });

  final int currentPage;
  final bool hasPrevious;
  final bool hasNext;
  final VoidCallback onPrevious;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: colors.always161B22,
        border: Border(top: BorderSide(color: colors.always30363D)),
      ),
      child: Row(
        children: [
          CustomOutlinedButton.big(
            text: 'Previous',
            onTap: hasPrevious ? onPrevious : null,
            textColor: hasPrevious ? colors.alwaysE6EDF3 : colors.always6E7681,
            borderColor: hasPrevious ? colors.always30363D : colors.always2D333B,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Center(
              child: Text(
                'Page $currentPage',
                style: TextStyle(
                  color: colors.always8B949E,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          CustomOutlinedButton.big(
            text: 'Next',
            onTap: hasNext ? onNext : null,
            textColor: hasNext ? colors.alwaysE6EDF3 : colors.always6E7681,
            borderColor: hasNext ? colors.always30363D : colors.always2D333B,
          ),
        ],
      ),
    );
  }
}
