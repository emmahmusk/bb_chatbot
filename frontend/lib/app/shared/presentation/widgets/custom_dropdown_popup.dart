import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:frontend/app/shared/classes/media/svgs.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_pop_up/custom_popup.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';

class CustomDropdownPopup<T> extends ConsumerWidget {
  final List<(String text, T value)> options;
  final (String text, T value) selectedValue;
  final ValueChanged<(String text, T value)> onChanged;
  final String header;
  final bool required;
  final double? height;
  const CustomDropdownPopup({
    super.key,
    required this.selectedValue,
    required this.options,
    required this.onChanged,
    required this.header,
    this.required = false,
    this.height,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return CustomPopUp(
      padding: const EdgeInsets.symmetric(vertical: 10),
      width: 300,
      radius: 12,
      popUp: SizedBox(
        height: height ?? 150,
        child: ListView.builder(
          itemBuilder: (context, index) {
            return Clickable(
              onClick: () {
                onChanged(options[index]);
                pop(context);
              },
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 14),
                color: colors.transparent,
                child: Text(
                  options[index].$1,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 14,
                    color: colors.alwaysBlack,
                  ),
                ),
              ),
            );
          },
          itemCount: options.length,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                header,
                style: TextStyle(
                  color: colors.alwaysBlack,
                  fontSize: 14,
                ),
              ),
              if (required) ...[
                const SizedBox(width: 4),
                Text(
                  "*",
                  style: TextStyle(
                    color: colors.alwaysB54708,
                    fontSize: 14,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 16),
            decoration: BoxDecoration(
              color: colors.always30363D.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: colors.always30363D,
                width: 1,
              ),
            ),
            child: Center(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      selectedValue.$1,
                      style: TextStyle(
                        fontSize: 14,
                        color: colors.alwaysBlack,
                      ),
                    ),
                  ),
                  RotatedBox(
                    quarterTurns: 0,
                    child: SvgPicture.asset(Svgs.chevron),
                  )
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
