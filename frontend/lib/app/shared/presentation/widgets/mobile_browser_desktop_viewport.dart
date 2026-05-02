import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

class MobileBrowserDesktopViewport extends StatelessWidget {
  const MobileBrowserDesktopViewport({
    super.key,
    required this.child,
  });

  final Widget child;

  static const double _minimumDesktopModeWidth = 560;
  static const double _maximumDesktopModeWidth = 820;
  static const double _desktopModeWidthMultiplier = 1.45;

  bool get _isMobileWebPlatform {
    if (!kIsWeb) {
      return false;
    }

    return defaultTargetPlatform == TargetPlatform.android ||
        defaultTargetPlatform == TargetPlatform.iOS;
  }

  EdgeInsets _scaleInsets(EdgeInsets source, double scale) {
    return EdgeInsets.fromLTRB(
      source.left / scale,
      source.top / scale,
      source.right / scale,
      source.bottom / scale,
    );
  }

  double _desktopModeWidthFor(Size actualSize) {
    final targetWidth = actualSize.width * _desktopModeWidthMultiplier;
    return targetWidth.clamp(
      _minimumDesktopModeWidth,
      _maximumDesktopModeWidth,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!_isMobileWebPlatform) {
      return child;
    }

    final mediaQuery = MediaQuery.of(context);
    final actualSize = mediaQuery.size;
    final desktopModeWidth = _desktopModeWidthFor(actualSize);
    final shouldEmulateDesktopViewport = actualSize.width < desktopModeWidth;

    if (!shouldEmulateDesktopViewport) {
      return child;
    }

    final scale = actualSize.width / desktopModeWidth;
    final virtualHeight = actualSize.height / scale;

    final desktopViewportMediaQuery = mediaQuery.copyWith(
      size: Size(desktopModeWidth, virtualHeight),
      padding: _scaleInsets(mediaQuery.padding, scale),
      viewPadding: _scaleInsets(mediaQuery.viewPadding, scale),
      viewInsets: _scaleInsets(mediaQuery.viewInsets, scale),
      systemGestureInsets: _scaleInsets(mediaQuery.systemGestureInsets, scale),
    );

    return SizedBox(
      width: actualSize.width,
      height: actualSize.height,
      child: ClipRect(
        child: OverflowBox(
          alignment: Alignment.topCenter,
          minWidth: desktopModeWidth,
          maxWidth: desktopModeWidth,
          minHeight: virtualHeight,
          maxHeight: virtualHeight,
          child: Transform.scale(
            alignment: Alignment.topCenter,
            scale: scale,
            transformHitTests: true,
            child: SizedBox(
              width: desktopModeWidth,
              height: virtualHeight,
              child: MediaQuery(
                data: desktopViewportMediaQuery,
                child: child,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
