import 'package:flutter/material.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/desktop/stock_profile_page.dart';
import 'package:frontend/app/modules/dashboard/presentation/responsive/mobile/mobile_stock_profile_page.dart';
import 'package:frontend/app/shared/presentation/widgets/responsive_builder.dart';

class StockProfileEntry extends StatelessWidget {
  const StockProfileEntry({
    super.key,
    required this.id,
  });

  final String id;

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      mobileBuilder: (_) => MobileStockProfilePage(id: id),
      desktopBuilder: (_) => StockProfilePage(id: id),
    );
  }
}
