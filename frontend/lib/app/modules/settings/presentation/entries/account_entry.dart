import 'package:flutter/widgets.dart';
import 'package:frontend/app/modules/settings/presentation/responsive/desktop/desktop_account_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class AccountEntry extends StatelessWidget {
  const AccountEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (_) => Container(),
      desktopBuilder: (_) => DesktopAccountPage(),
    );
  }
}
