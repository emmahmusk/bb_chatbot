import 'package:flutter/material.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';

class BullBearLogo extends StatefulWidget {
  final bool shouldAnimate;
  final double size;
  final Color? color;
  const BullBearLogo({
    super.key,
    required this.shouldAnimate,
    this.color,
    this.size = 60,
  });

  factory BullBearLogo.small({
    bool shouldAnimate = true,
    // Color? color,
  }) {
    return BullBearLogo(
      size: 10,
      shouldAnimate: shouldAnimate,
      // color: color,
    );
  }

  factory BullBearLogo.mid({
    bool shouldAnimate = true,
    Color? color,
  }) {
    return BullBearLogo(
      size: 70,
      shouldAnimate: shouldAnimate,
      // color: color,
    );
  }

  factory BullBearLogo.large({
    bool shouldAnimate = true,
    Color? color,
  }) {
    return BullBearLogo(
      size: 100,
      shouldAnimate: shouldAnimate,
      // color: color,
    );
  }

  @override
  State<BullBearLogo> createState() => _BullBearLogoState();
}

class _BullBearLogoState extends State<BullBearLogo>
    with SingleTickerProviderStateMixin {
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
        width: widget.size,
        fit: BoxFit.contain,
        // color: widget.color,
      ),
    );
  }
}
