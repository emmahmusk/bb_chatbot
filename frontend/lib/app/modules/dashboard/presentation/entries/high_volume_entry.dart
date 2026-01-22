import 'package:flutter/material.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/desktop_high_volume_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class HighVolumeEntry extends StatelessWidget {
  const HighVolumeEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (context) => Container(),
      desktopBuilder: (context) => DesktopHighVolumePage(),
    );
  }
}
