import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

// class BetOption extends ConsumerWidget {
//   const BetOption({
//     super.key,
//     required this.title,
//     required this.value,
//     this.onClick,
//   });
//   final String title;
//   final double value;
//   final Function(double)? onClick;

//   @override
//   Widget build(BuildContext context, WidgetRef ref) {
//     final colors = ref.watch(appThemeProvider).colors;
//     return Column(
//       children: [
//         Container(
//           width: 144,
//           height: 36,
//           padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
//           decoration: BoxDecoration(
//             borderRadius: BorderRadius.only(
//               topLeft: Radius.circular(12),
//               topRight: Radius.circular(12),
//               bottomLeft: Radius.circular(4),
//               bottomRight: Radius.circular(4),
//             ),
//             color: colors.always1F242C,
//           ),
//           child: Center(
//             child: Text(
//               title,
//               style: TextStyle(
//                 fontSize: 12,
//                 fontWeight: FontWeight.w400,
//                 color: colors.always6E7681,
//               ),
//             ),
//           ),
//         ),
//         const SizedBox(height: 4),
//         Clickable(
//           onClick: () => onClick?.call(value),
//           child: Container(
//             width: 144,
//             height: 40,
//             padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
//             decoration: BoxDecoration(
//               borderRadius: BorderRadius.only(
//                 bottomLeft: Radius.circular(12),
//                 bottomRight: Radius.circular(12),
//                 topLeft: Radius.circular(4),
//                 topRight: Radius.circular(4),
//               ),
//               color: colors.always1F242C,
//             ),
//             child: Center(
//               child: Text(
//                 value.toString(),
//                 style: TextStyle(
//                   fontSize: 18,
//                   fontWeight: FontWeight.w500,
//                   color: colors.alwaysWhite,
//                 ),
//               ),
//             ),
//           ),
//         ),
//       ],
//     );
//   }
// }

class BetOption extends ConsumerWidget {
  const BetOption({
    super.key,
    required this.title,
    required this.value,
    required this.isSelected,
    required this.onClick,
  });

  final String title;
  final double value;
  final bool isSelected;
  final VoidCallback onClick;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    // Background and text colors depending on selection
    final bgColor = isSelected ? colors.alwaysWhite : colors.always1F242C;
    final titleColor = isSelected ? colors.always30363D : colors.always6E7681;
    final valueColor = isSelected ? colors.always30363D : colors.alwaysWhite;
    final valueSize = isSelected ? FontWeight.w600 : FontWeight.w500;

    return Clickable(
      onClick: onClick,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 144,
            height: 36,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(12),
                topRight: Radius.circular(12),
                bottomLeft: Radius.circular(4),
                bottomRight: Radius.circular(4),
              ),
            ),
            child: Text(
              title,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w400,
                color: titleColor,
              ),
            ),
          ),
          const SizedBox(height: 4),
          Container(
            width: 144,
            height: 40,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(12),
                bottomRight: Radius.circular(12),
                topLeft: Radius.circular(4),
                topRight: Radius.circular(4),
              ),
            ),
            child: Text(
              value.toStringAsFixed(2),
              style: TextStyle(
                fontSize: 18,
                fontWeight: valueSize,
                color: valueColor,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
