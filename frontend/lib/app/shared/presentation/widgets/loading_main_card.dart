import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/bullbear_logo.dart';
import 'package:frontend/app/shared/presentation/widgets/main_card.dart';
 
class LoadingMainCard extends ConsumerWidget {
  final Color? color;
  const LoadingMainCard({
    super.key,
    this.color,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    
    return Center(
      child: MainCard(
        // color: color ?? colors.primary,
        child: BullBearLogo.mid(),
      ),
    );
  }
}
