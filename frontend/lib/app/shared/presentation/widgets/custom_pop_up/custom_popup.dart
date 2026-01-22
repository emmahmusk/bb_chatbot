import 'package:flutter/material.dart';

import 'custom_popup_item.dart';

class CustomPopUp extends StatelessWidget {
  final Widget child;
  final Widget popUp;
  final double width;
  final EdgeInsetsGeometry padding;
  final double radius;

  const CustomPopUp({
    super.key,
    required this.child,
    required this.popUp,
    this.padding = const EdgeInsets.symmetric(horizontal: 90, vertical: 90),
    this.width = 200,
    this.radius = 3,
  });

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton(
      padding: padding,
      menuPadding: padding,
      tooltip: "",
      constraints: BoxConstraints(maxWidth: width),
      position: PopupMenuPosition.under,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(radius),
      ),
      offset: const Offset(0, 0),
      itemBuilder: (context) {
        return [
          CustomPopUpItem(
            child: SizedBox(
              width: double.maxFinite,
              child: popUp,
            ),
          ),
        ];
      },
      child: child,
    );
  }
}
