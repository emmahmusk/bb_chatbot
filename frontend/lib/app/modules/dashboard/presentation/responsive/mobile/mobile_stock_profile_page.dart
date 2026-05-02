import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/providers/recently_visited_provider.dart';
import 'package:frontend/app/modules/dashboard/data/models/visited_stock_model.dart';
import 'package:frontend/app/modules/dashboard/data/models/user_stock_selection_model.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/stock_selection_provider.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/presentation/widgets/loading_main_card.dart';
import 'package:frontend/app/shared/providers/preferences_provider.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MobileStockProfilePage extends ConsumerStatefulWidget {
  const MobileStockProfilePage({
    super.key,
    required this.id,
  });

  final String id;

  @override
  ConsumerState<MobileStockProfilePage> createState() =>
      _MobileStockProfilePageState();
}

class _MobileStockProfilePageState extends ConsumerState<MobileStockProfilePage> {
  final ScrollController _scrollController = ScrollController();

  Map<String, dynamic>? _market;
  bool _isLoading = true;
  String _htmlContent = '';
  String _preferredOdds = 'P';

  @override
  void initState() {
    super.initState();
    _loadPreferredOddsType();
    _fetchMarket();

    ref.listen<String>(oddsTypeProvider, (previous, next) {
      if (mounted && previous != next) {
        setState(() {
          _preferredOdds = next;
        });
      }
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadPreferredOddsType() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('odds_type');
    if (!mounted) return;
    setState(() {
      _preferredOdds = (saved != null && ['A', 'D', 'F', 'P'].contains(saved))
          ? saved
          : ref.read(oddsTypeProvider);
    });
  }

  Future<void> _fetchMarket() async {
    try {
      final response = await http.get(
        Uri.parse('https://api.bbbprediction.com/bet/markets/${widget.id}/'),
      );

      if (response.statusCode != 200) {
        if (!mounted) return;
        setState(() {
          _isLoading = false;
        });
        return;
      }

      final data = json.decode(response.body) as Map<String, dynamic>;

      final stock = data['stock'] as Map<String, dynamic>? ?? <String, dynamic>{};
      final recentlyVisited = VisitedStockModel(
        imageUrl: stock['url']?.toString() ?? '',
        companyName: stock['company_name']?.toString() ?? '',
        symbol: stock['symbol']?.toString() ?? '',
        expiry: data['expiry_date']?.toString() ?? '',
        id: data['id'] as int,
      );
      final currentList = ref.read(recentlyVisitedProvider);
      final alreadyExists = currentList.any((item) => item.id == recentlyVisited.id);
      if (!alreadyExists) {
        ref.read(recentlyVisitedProvider.notifier).add(recentlyVisited);
      }

      if (!mounted) return;

      setState(() {
        _market = data;
        _htmlContent = _buildTradingViewHtml(stock['symbol']?.toString() ?? '');
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
    }
  }

  String _buildTradingViewHtml(String symbol) {
    return '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    html, body {
      margin: 0;
      padding: 0;
      background-color: transparent;
      width: 100%;
      height: 100%;
      overflow: hidden;
    }
    .tradingview-widget-container {
      width: 100%;
      height: 100%;
    }
    .tradingview-widget-container__widget {
      width: 100%;
      height: 100%;
    }
  </style>
</head>
<body>
  <div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
    {
      "symbols": [["$symbol", "$symbol|1D"]],
      "chartType": "area",
      "colorTheme": "dark",
      "backgroundColor": "transparent",
      "isTransparent": true,
      "autosize": true,
      "locale": "en"
    }
    </script>
  </div>
</body>
</html>
''';
  }

  String _getOdds(
    Map<String, dynamic>? oddsData, {
    double? impliedOdds,
  }) {
    final odds = oddsData ?? <String, dynamic>{};
    switch (_preferredOdds) {
      case 'A':
        return odds['american']?.toString() ?? 'N/A';
      case 'F':
        return odds['fractional']?.toString() ?? 'N/A';
      case 'P':
        if (impliedOdds != null && impliedOdds > 0) {
          return '${(impliedOdds * 100).toStringAsFixed(2)}%';
        }
        return odds['decimal']?.toString() ?? 'N/A';
      case 'D':
      default:
        return odds['decimal']?.toString() ?? 'N/A';
    }
  }

  String _formatExpiry(String value) {
    try {
      if (value.contains(',')) {
        return DateFormat('MMM d, yyyy').format(
          DateFormat('EEE, dd MMM yyyy').parse(value),
        );
      }
      return DateFormat('MMM d, yyyy').format(DateTime.parse(value));
    } catch (_) {
      return value;
    }
  }

  double? _resolveLastPrice(Map<String, dynamic> market) {
    final stock = market['stock'] as Map<String, dynamic>? ?? {};
    for (final value in [
      market['last_price'],
      market['latest_price'],
      market['current_price'],
      market['price'],
      stock['last_price'],
      stock['latest_price'],
      stock['current_price'],
      stock['price'],
      stock['close'],
      stock['previous_close'],
    ]) {
      if (value == null) {
        continue;
      }
      final parsed = double.tryParse(value.toString());
      if (parsed != null) {
        return parsed;
      }
    }
    return null;
  }

  String _routeToMarketId(int marketId) {
    final competitionId = GoRouterState.of(context).uri.queryParameters['competitionId'];
    if (competitionId == null || competitionId.isEmpty) {
      return '${DashboardRoutes.stockProfile}?id=$marketId';
    }
    return '${DashboardRoutes.stockProfile}?id=$marketId&competitionId=$competitionId';
  }

  String _backRoute() {
    final competitionId = GoRouterState.of(context).uri.queryParameters['competitionId'];
    if (competitionId == null || competitionId.isEmpty) {
      return DashboardRoutes.trending;
    }
    return Uri(
      path: DashboardRoutes.trending,
      queryParameters: {'competitionId': competitionId},
    ).toString();
  }

  Future<List<String>> _fetchExpiryDates(String symbol) async {
    final response = await http.get(
      Uri.parse('https://api.bbbprediction.com/bet/expiries/?symbol=$symbol'),
    );
    if (response.statusCode != 200) {
      return const <String>[];
    }
    final decoded = json.decode(response.body) as Map<String, dynamic>;
    return List<String>.from(decoded['expiries'] ?? const <String>[]);
  }

  Future<List<Map<String, dynamic>>> _fetchStrikeOptions(
    String symbol,
    String expiry,
  ) async {
    final response = await http.get(
      Uri.parse(
        'https://api.bbbprediction.com/bet/markets/?search=$symbol&expiry=$expiry',
      ),
    );
    if (response.statusCode != 200) {
      return const <Map<String, dynamic>>[];
    }
    final decoded = json.decode(response.body) as Map<String, dynamic>;
    return List<Map<String, dynamic>>.from(decoded['results'] ?? const []);
  }

  Future<void> _selectExpiryAndStrike() async {
    final market = _market;
    if (market == null) return;
    final stock = market['stock'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final symbol = stock['symbol']?.toString();
    if (symbol == null || symbol.isEmpty) return;

    final expiries = await _fetchExpiryDates(symbol);
    if (!mounted || expiries.isEmpty) return;

    final selectedExpiry = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => _SelectionSheet(
        title: 'Select expiry',
        child: ListView.separated(
          shrinkWrap: true,
          itemCount: expiries.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, index) => _SheetAction(
            label: _formatExpiry(expiries[index]),
            onTap: () => Navigator.of(context).pop(expiries[index]),
          ),
        ),
      ),
    );

    if (!mounted || selectedExpiry == null) return;

    final strikes = await _fetchStrikeOptions(symbol, selectedExpiry);
    if (!mounted || strikes.isEmpty) return;

    final selectedMarketId = await showModalBottomSheet<int>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => _SelectionSheet(
        title: 'Select strike',
        child: ListView.separated(
          shrinkWrap: true,
          itemCount: strikes.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final strike = strikes[index];
            final overOdds = _getOdds(
              Map<String, dynamic>.from(strike['odds_over'] ?? const {}),
              impliedOdds: double.tryParse(
                strike['implied_odds_over']?.toString() ?? '',
              ),
            );
            final underOdds = _getOdds(
              Map<String, dynamic>.from(strike['odds_under'] ?? const {}),
              impliedOdds: double.tryParse(
                strike['implied_odds_under']?.toString() ?? '',
              ),
            );

            return _SheetStrikeAction(
              strikeLabel:
                  '\$${(double.tryParse(strike['target_price'].toString()) ?? 0).toStringAsFixed(2)}',
              overOdds: overOdds,
              underOdds: underOdds,
              onTap: () => Navigator.of(context).pop(strike['id'] as int),
            );
          },
        ),
      ),
    );

    if (!mounted || selectedMarketId == null) return;
    context.go(_routeToMarketId(selectedMarketId));
  }

  void _toggleOutcome(String chosenOutcome) {
    final market = _market;
    if (market == null) return;

    final int marketId = market['id'] as int;
    final selectedStocks = ref.read(selectedStockProvider);
    final isAlreadySelected = selectedStocks.any(
      (stock) =>
          stock.marketId == marketId &&
          stock.chosenOutcome.toLowerCase() == chosenOutcome,
    );

    if (isAlreadySelected) {
      ref.read(selectedStockProvider.notifier).remove(marketId);
      return;
    }

    final stock = market['stock'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final oddsMap = Map<String, dynamic>.from(
      chosenOutcome == 'over'
          ? (market['odds_over'] ?? const {})
          : (market['odds_under'] ?? const {}),
    );
    final impliedOdds = double.tryParse(
      (chosenOutcome == 'over'
              ? market['implied_odds_over']
              : market['implied_odds_under'])
          ?.toString() ??
          '',
    );

    ref.read(selectedStockProvider.notifier).insertOrUpdate(
          SelectedStockModel(
            marketId: marketId,
            marketName: stock['company_name']?.toString() ?? stock['symbol']?.toString() ?? '',
            chosenOutcome: chosenOutcome,
            odds: _getOdds(oddsMap, impliedOdds: impliedOdds),
            decimalOdds: oddsMap['decimal']?.toString(),
            companyName: stock['company_name']?.toString() ?? '',
            companySymbol: stock['symbol']?.toString() ?? '',
            logoUrl: stock['url']?.toString() ?? '',
            targetPrice:
                double.tryParse(market['target_price']?.toString() ?? ''),
            expiryDate: market['expiry_date']?.toString() ?? '',
          ),
        );
  }

  Future<void> _showFullScreenGraph() async {
    if (_htmlContent.isEmpty) return;

    await showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) {
        final size = MediaQuery.of(ctx).size;
        return Dialog(
          insetPadding: const EdgeInsets.all(12),
          backgroundColor: Colors.transparent,
          child: Container(
            width: size.width,
            height: size.height * 0.82,
            decoration: BoxDecoration(
              color: const Color(0xFF0F131B),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Stack(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 56, 12, 12),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(18),
                    child: InAppWebView(
                      initialData: InAppWebViewInitialData(data: _htmlContent),
                    ),
                  ),
                ),
                Positioned(
                  top: 14,
                  right: 14,
                  child: IconButton(
                    onPressed: () => Navigator.of(ctx).pop(),
                    icon: const Icon(Icons.close, color: Colors.white),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;

    if (_isLoading) {
      return const Center(child: LoadingMainCard());
    }

    final market = _market;
    if (market == null) {
      return Center(
        child: Text(
          'We could not load this market right now.',
          style: TextStyle(color: colors.alwaysWhite),
        ),
      );
    }

    final stock = market['stock'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final lastPrice = _resolveLastPrice(market);
    final marketId = market['id'] as int;
    final selectedStocks = ref.watch(selectedStockProvider);
    final isOverSelected = selectedStocks.any(
      (item) => item.marketId == marketId && item.chosenOutcome == 'over',
    );
    final isUnderSelected = selectedStocks.any(
      (item) => item.marketId == marketId && item.chosenOutcome == 'under',
    );

    final overOdds = _getOdds(
      Map<String, dynamic>.from(market['odds_over'] ?? const {}),
      impliedOdds: double.tryParse(market['implied_odds_over']?.toString() ?? ''),
    );
    final underOdds = _getOdds(
      Map<String, dynamic>.from(market['odds_under'] ?? const {}),
      impliedOdds: double.tryParse(market['implied_odds_under']?.toString() ?? ''),
    );

    return Scrollbar(
      controller: _scrollController,
      thumbVisibility: true,
      child: ListView(
        controller: _scrollController,
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: [
          Row(
            children: [
              IconButton(
                onPressed: () => context.go(_backRoute()),
                style: IconButton.styleFrom(
                  backgroundColor: colors.always30363D.withValues(alpha: 0.24),
                ),
                icon: Icon(Icons.arrow_back_rounded, color: colors.alwaysWhite),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Stock Contract',
                  style: TextStyle(
                    color: colors.alwaysWhite,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: colors.always30363D),
              gradient: LinearGradient(
                colors: [
                  colors.always30363D.withValues(alpha: 0.34),
                  colors.primary.withValues(alpha: 0.98),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _StockProfileLogo(
                      symbol: stock['symbol']?.toString() ?? '',
                      logoUrl: stock['url']?.toString(),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            stock['company_name']?.toString() ??
                                stock['symbol']?.toString() ??
                                'Unknown stock',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: colors.alwaysWhite,
                              fontSize: 22,
                              fontWeight: FontWeight.w800,
                              height: 1.1,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            '\$${stock['symbol']?.toString() ?? ''}',
                            style: TextStyle(
                              color: colors.alwaysWhite.withValues(alpha: 0.68),
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _ProfilePill(
                      icon: Icons.event_outlined,
                      label: _formatExpiry(market['expiry_date']?.toString() ?? ''),
                    ),
                    _ProfilePill(
                      iconAsset: Pngs.strikePrice,
                      label:
                          '\$${(double.tryParse(market['target_price']?.toString() ?? '') ?? 0).toStringAsFixed(2)} strike',
                    ),
                    if (lastPrice != null)
                      _ProfilePill(
                        icon: Icons.show_chart_rounded,
                        label: 'Last \$${lastPrice.toStringAsFixed(2)}',
                      ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            height: 260,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: colors.always30363D),
              color: colors.always161B22,
            ),
            child: Stack(
              children: [
                Positioned.fill(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(22),
                    child: _htmlContent.isEmpty
                        ? const Center(child: LoadingMainCard())
                        : InAppWebView(
                            initialData: InAppWebViewInitialData(data: _htmlContent),
                          ),
                  ),
                ),
                Positioned(
                  right: 12,
                  top: 12,
                  child: GestureDetector(
                    onTap: _showFullScreenGraph,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.42),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.open_in_full_rounded, size: 14, color: Colors.white),
                          SizedBox(width: 6),
                          Text(
                            'Expand',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: colors.always30363D),
              color: colors.always161B22,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Build your prediction',
                        style: TextStyle(
                          color: colors.alwaysWhite,
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    GestureDetector(
                      onTap: _selectExpiryAndStrike,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: colors.alwaysWhite.withValues(alpha: 0.24)),
                        ),
                        child: Text(
                          'Change',
                          style: TextStyle(
                            color: colors.alwaysWhite,
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  'Pick a direction and we will add it straight to your prediction slip.',
                  style: TextStyle(
                    color: colors.alwaysWhite.withValues(alpha: 0.65),
                    fontSize: 13,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _DirectionCard(
                        title: 'Over',
                        odds: overOdds,
                        selected: isOverSelected,
                        onTap: () => _toggleOutcome('over'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _DirectionCard(
                        title: 'Under',
                        odds: underOdds,
                        selected: isUnderSelected,
                        onTap: () => _toggleOutcome('under'),
                      ),
                    ),
                  ],
                ),
                if (isOverSelected || isUnderSelected) ...[
                  const SizedBox(height: 14),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 12,
                    ),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(14),
                      color: Colors.greenAccent.withValues(alpha: 0.12),
                      border: Border.all(
                        color: Colors.greenAccent.withValues(alpha: 0.2),
                      ),
                    ),
                    child: Text(
                      'Added to prediction slip. Open the slip from the dashboard footer when you are ready.',
                      style: TextStyle(
                        color: colors.alwaysWhite,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StockProfileLogo extends StatelessWidget {
  const _StockProfileLogo({
    required this.symbol,
    required this.logoUrl,
  });

  final String symbol;
  final String? logoUrl;

  @override
  Widget build(BuildContext context) {
    if (logoUrl != null && logoUrl!.isNotEmpty) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Image.network(
          logoUrl!,
          width: 54,
          height: 54,
          fit: BoxFit.cover,
        ),
      );
    }

    return Container(
      width: 54,
      height: 54,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        symbol.substring(0, symbol.length >= 2 ? 2 : 1).toUpperCase(),
        style: const TextStyle(
          color: Colors.black,
          fontWeight: FontWeight.w800,
          fontSize: 15,
        ),
      ),
    );
  }
}

class _ProfilePill extends ConsumerWidget {
  const _ProfilePill({
    required this.label,
    this.icon,
    this.iconAsset,
  });

  final String label;
  final IconData? icon;
  final String? iconAsset;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: colors.always30363D.withValues(alpha: 0.34),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null)
            Icon(icon, size: 14, color: colors.alwaysWhite.withValues(alpha: 0.72)),
          if (iconAsset != null)
            Image.asset(
              iconAsset!,
              width: 14,
              height: 14,
              fit: BoxFit.contain,
            ),
          const SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(
              color: colors.alwaysWhite,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _DirectionCard extends ConsumerWidget {
  const _DirectionCard({
    required this.title,
    required this.odds,
    required this.selected,
    required this.onTap,
  });

  final String title;
  final String odds;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: selected ? colors.alwaysWhite : colors.always30363D.withValues(alpha: 0.24),
          border: Border.all(
            color: selected ? colors.alwaysWhite : colors.always30363D,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: TextStyle(
                color: selected ? colors.primary : colors.alwaysWhite.withValues(alpha: 0.7),
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              odds,
              style: TextStyle(
                color: selected ? colors.primary : colors.alwaysWhite,
                fontSize: 20,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SelectionSheet extends ConsumerWidget {
  const _SelectionSheet({
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return SafeArea(
      child: Container(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.82,
        ),
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
        decoration: BoxDecoration(
          color: colors.primary,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          border: Border.all(color: colors.always30363D),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 42,
                height: 5,
                decoration: BoxDecoration(
                  color: colors.alwaysWhite.withValues(alpha: 0.32),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: TextStyle(
                color: colors.alwaysWhite,
                fontSize: 18,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 14),
            Flexible(child: child),
          ],
        ),
      ),
    );
  }
}

class _SheetAction extends ConsumerWidget {
  const _SheetAction({
    required this.label,
    required this.onTap,
  });

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.always30363D),
          color: colors.always30363D.withValues(alpha: 0.22),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: colors.alwaysWhite,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

class _SheetStrikeAction extends ConsumerWidget {
  const _SheetStrikeAction({
    required this.strikeLabel,
    required this.overOdds,
    required this.underOdds,
    required this.onTap,
  });

  final String strikeLabel;
  final String overOdds;
  final String underOdds;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: colors.always30363D),
          color: colors.always30363D.withValues(alpha: 0.22),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              strikeLabel,
              style: TextStyle(
                color: colors.alwaysWhite,
                fontSize: 15,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _MiniOddsPill(title: 'Over', odds: overOdds),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _MiniOddsPill(title: 'Under', odds: underOdds),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MiniOddsPill extends ConsumerWidget {
  const _MiniOddsPill({
    required this.title,
    required this.odds,
  });

  final String title;
  final String odds;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: colors.alwaysWhite.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              color: colors.alwaysWhite.withValues(alpha: 0.62),
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            odds,
            style: TextStyle(
              color: colors.alwaysWhite,
              fontSize: 14,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
