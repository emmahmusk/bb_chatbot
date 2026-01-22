import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';

class MarketPhoto extends ConsumerWidget {
  final String? url;
  final double size;
  final double borderRadius;
  final bool hasBorder;
  final String? heroTag;
  final bool showDialogOnTap;
  final String stockSymbol;
  const MarketPhoto({
    super.key,
    required this.url,
    this.size = 40,
    this.borderRadius = 12,
    this.hasBorder = true,
    this.heroTag,
    this.showDialogOnTap = false,
    required this.stockSymbol,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    final hasProfilePicture = url != null && url!.isNotEmpty;
    Widget body = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(borderRadius),
        color: colors.always30363D.withValues(alpha: 0.2),
        border: hasBorder
            ? Border.all(
                color: colors.always30363D,
                width: 2,
              )
            : null,
        image: !hasProfilePicture
            ? null
            : DecorationImage(
                image: NetworkImage(url!),
                fit: BoxFit.cover,
              ),
      ),
      child: hasProfilePicture
          ? null
          : Center(
              child: Text(
                stockSymbol[0].toUpperCase(),
                style: TextStyle(
                  color: colors.alwaysWhite,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
    );
    // if (heroTag != null) {
    //   body = Hero(
    //     tag: heroTag!,
    //     child: body,
    //   );
    // }
    // if (showDialogOnTap) {
    //   body = GestureDetector(
    //     onTap: () {
    //       showBlurDialog(
    //         context,
    //         barrierDismissible: true,
    //         usesHero: true,
    //         child: MemberPhotoDialog(
    //           heroTag: heroTag!,
    //           photoUrl: url,
    //         ),
    //       );
    //     },
    //     child: body,
    //   );
    // }
    return body;
  }
}
