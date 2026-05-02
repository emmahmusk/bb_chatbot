import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

class MobileBrowserDesktopViewport extends StatelessWidget {
  const MobileBrowserDesktopViewport({
    super.key,
    required this.child,
  });

  final Widget child;

  static const double _desktopModeWidth = 980;

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

  @override
  Widget build(BuildContext context) {
    if (!_isMobileWebPlatform) {
      return child;
    }

    final mediaQuery = MediaQuery.of(context);
    final actualSize = mediaQuery.size;
    final shouldEmulateDesktopViewport = actualSize.width < _desktopModeWidth;

    if (!shouldEmulateDesktopViewport) {
      return child;
    }

    final scale = actualSize.width / _desktopModeWidth;
    final virtualHeight = actualSize.height / scale;

    final desktopViewportMediaQuery = mediaQuery.copyWith(
      size: Size(_desktopModeWidth, virtualHeight),
      padding: _scaleInsets(mediaQuery.padding, scale),
      viewPadding: _scaleInsets(mediaQuery.viewPadding, scale),
      viewInsets: _scaleInsets(mediaQuery.viewInsets, scale),
      systemGestureInsets: _scaleInsets(mediaQuery.systemGestureInsets, scale),
    );

    return SizedBox(
      width: actualSize.width,
      height: actualSize.height,
      child: ClipRect(
        child: FittedBox(
          fit: BoxFit.fitWidth,
          alignment: Alignment.topCenter,
          child: SizedBox(
            width: _desktopModeWidth,
            height: virtualHeight,
            child: MediaQuery(
              data: desktopViewportMediaQuery,
              child: child,
            ),
          ),
        ),
      ),
    );
  }
}
