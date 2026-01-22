import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/extensions/list_extension.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class CustomTableRow extends ConsumerWidget {
  final List<String> data;
  final int rowIndex;
  final Widget Function(
    String value,
    Widget old,
    int columnIndex,
    int rowIndex,
  )? cellDecorator;

  const CustomTableRow({
    super.key,
    required this.data,
    required this.rowIndex,
    this.cellDecorator,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(
            vertical: 25,
            horizontal: 24,
          ),
          child: Row(
            children: [
              for (final (i, text) in data.enumerate())
                Expanded(
                  child: Builder(
                    builder: (context) {
                      final x = Text(
                        text,
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                        style: TextStyle(
                          fontSize: 12,
                          color: colors.alwaysBlack,
                          fontWeight: FontWeight.w500,
                        ),
                      );
                      if (cellDecorator != null) {
                        return cellDecorator!(text, x, i, rowIndex);
                      }
                      return x;
                    },
                  ),
                )
            ],
          ),
        ),
        const CustomDivider(),
      ],
    );
  }
}
