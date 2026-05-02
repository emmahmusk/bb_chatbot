import 'package:flutter/material.dart';

class Clickable extends StatelessWidget {
  final VoidCallback? onClick;
  final Widget child;
  const Clickable({
    super.key,
    this.onClick,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onClick,
        child: child,
      ),
    );
  }
}
