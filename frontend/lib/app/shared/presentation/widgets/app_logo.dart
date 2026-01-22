import 'package:flutter/material.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';

class AppLogo extends StatefulWidget {
  final bool shouldAnimate;
  final double size;
  final Color? color;
  const AppLogo({
    super.key,
    required this.shouldAnimate,
    this.color,
    this.size = 60,
  });

  factory AppLogo.small({
    bool shouldAnimate = true,
    Color? color,
  }) {
    return AppLogo(
      size: 30,
      shouldAnimate: shouldAnimate,
      color: color,
    );
  }

  factory AppLogo.mid({
    bool shouldAnimate = true,
    Color? color,
  }) {
    return AppLogo(
      size: 70,
      shouldAnimate: shouldAnimate,
      color: color,
    );
  }

  factory AppLogo.large({
    bool shouldAnimate = true,
    Color? color,
  }) {
    return AppLogo(
      size: 100,
      shouldAnimate: shouldAnimate,
      color: color,
    );
  }

  @override
  State<AppLogo> createState() => _AppLogoState();
}

class _AppLogoState extends State<AppLogo> with SingleTickerProviderStateMixin {
  late final AnimationController controller;
  late final Animation<double> scale;

  @override
  void initState() {
    super.initState();
    controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    const max = 1.5;
    const min = 0.8;

    scale = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween(begin: min, end: max).chain(
          CurveTween(curve: Curves.easeOut),
        ),
        weight: 8,
      ),
      TweenSequenceItem(
        tween: Tween(begin: max, end: min).chain(
          CurveTween(curve: Curves.ease),
        ),
        weight: 13,
      ),
      TweenSequenceItem(
        tween: ConstantTween<double>(min),
        weight: 10, // Pause
      ),
      TweenSequenceItem(
        tween: Tween(begin: min, end: max).chain(
          CurveTween(curve: Curves.easeOut),
        ),
        weight: 8,
      ),
      TweenSequenceItem(
        tween: Tween(begin: max, end: min).chain(
          CurveTween(curve: Curves.ease),
        ),
        weight: 13,
      ),
      TweenSequenceItem(
        tween: ConstantTween<double>(min),
        weight: 50, // Pause
      ),
    ]).animate(controller);

    if (widget.shouldAnimate) {
      controller.repeat();
    }
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: scale,
      child: Image.asset(
        Pngs.bullbearLogo,
        height: widget.size,
        color: widget.color,
      ),
    );
  }
}
