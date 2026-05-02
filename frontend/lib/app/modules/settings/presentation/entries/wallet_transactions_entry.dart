import 'package:flutter/widgets.dart';
import 'package:frontend/app/modules/settings/presentation/responsive/desktop/desktop_wallet_transactions_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class WalletTransactionsEntry extends StatelessWidget {
  const WalletTransactionsEntry({super.key});

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      hasScaffold: true,
      mobileBuilder: (_) => DesktopWalletTransactionsPage(),
      desktopBuilder: (_) => DesktopWalletTransactionsPage(),
    );
  }
}
