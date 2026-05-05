import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/data/models/market_model_new.dart';
import 'package:frontend/app/modules/dashboard/data/models/user_stock_selection_model.dart';
import 'package:frontend/app/modules/dashboard/presentation/dashboard_routes.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/get_markets_provider_new.dart';
import 'package:frontend/app/modules/dashboard/presentation/providers/stock_selection_provider.dart';
import 'package:frontend/app/shared/classes/media/pngs.dart';
import 'package:frontend/app/shared/presentation/widgets/loading_main_card.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MobileMarketsPage extends ConsumerStatefulWidget {
  const MobileMarketsPage({
    super.key,
    required this.title,
    required this.subtitle,
    required this.path,
    required this.pagePreferenceKey,
    this.queryParams = const <String, String>{},
  });

  final String title;
  final String subtitle;
  final String path;
  final String pagePreferenceKey;
  final Map<String, String> queryParams;

  @override
  ConsumerState<MobileMarketsPage> createState() => _MobileMarketsPageState();
}

class _MobileMarketsPageState extends ConsumerState<MobileMarketsPage> {
  final ScrollController _scrollController = ScrollController();
  final Map<int, MarketModel> _marketOverrides = {};
  static const Duration _autoRefreshInterval = Duration(seconds: 30);

  String _preferredOdds = 'P';
  String _currentPage = '1';
  bool _prefsLoaded = false;
  bool _didFetchForThisActivation = false;
  bool _isAutoRefreshing = false;
  bool _isActivationLoading = false;
  Timer? _autoRefreshTimer;

  @override
  void initState() {
    super.initState();
    _loadPreferences();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _autoRefreshTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _startAutoRefresh() {
    _autoRefreshTimer?.cancel();
    _autoRefreshTimer = Timer.periodic(_autoRefreshInterval, (_) {
      _pollCurrentPage();
    });
  }

  Future<void> _loadPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    final savedOdds = prefs.getString('odds_type');
    final savedPage = prefs.getString(widget.pagePreferenceKey);

    if (!mounted) return;

    setState(() {
      if (savedOdds != null && ['A', 'D', 'F', 'P'].contains(savedOdds)) {
        _preferredOdds = savedOdds;
      }
      if (savedPage != null && savedPage.isNotEmpty) {
        _currentPage = savedPage;
      }
      _prefsLoaded = true;
    });
  }

  Future<void> _refreshForActivation() async {
    final prefs = await SharedPreferences.getInstance();
    final savedOdds = prefs.getString('odds_type');
    final savedPage = prefs.getString(widget.pagePreferenceKey);

    final nextOdds =
        savedOdds != null && ['A', 'D', 'F', 'P'].contains(savedOdds)
            ? savedOdds
            : _preferredOdds;
    final nextPage =
        savedPage != null && savedPage.isNotEmpty ? savedPage : _currentPage;

    if (!mounted) return;

    setState(() {
      _preferredOdds = nextOdds;
      _currentPage = nextPage;
      _marketOverrides.clear();
      _isActivationLoading = true;
    });

    try {
      await ref.read(getMarketsProviderNew.notifier).get(
        queryParams: {
          ...widget.queryParams,
          'page': nextPage,
        },
      );
    } finally {
      if (!mounted) return;
      setState(() {
        _isActivationLoading = false;
      });
    }
  }

  Future<void> _fetchPage(String page) async {
    await ref.read(getMarketsProviderNew.notifier).get(
      queryParams: {
        ...widget.queryParams,
        'page': page,
      },
    );

    if (!mounted) return;

    setState(() {
      _marketOverrides.clear();
    });
  }

  bool _isCurrentRoute() {
    if (!mounted) return false;
    return GoRouterState.of(context).uri.path == widget.path;
  }

  Future<void> _pollCurrentPage() async {
    if (!_prefsLoaded || !_isCurrentRoute() || _isAutoRefreshing) {
      return;
    }

    _isAutoRefreshing = true;
    try {
      await ref.read(getMarketsProviderNew.notifier).get(
        queryParams: {
          ...widget.queryParams,
          'page': _currentPage,
        },
        preserveState: true,
      );
    } finally {
      _isAutoRefreshing = false;
    }
  }

  Future<void> _goToPage(int page) async {
    final pageStr = page.toString();
    if (_currentPage == pageStr) return;

    setState(() {
      _currentPage = pageStr;
    });

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(widget.pagePreferenceKey, pageStr);
    await _fetchPage(pageStr);

    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        0,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOutCubic,
      );
    }
  }

  void _toggleSelection(MarketModel market, String chosenOutcome) {
    final selectedStocks = ref.read(selectedStockProvider);
    final isAlreadySelected = selectedStocks.any(
      (stock) =>
          stock.marketId == market.id &&
          stock.chosenOutcome.toLowerCase() == chosenOutcome,
    );

    if (isAlreadySelected) {
      ref.read(selectedStockProvider.notifier).remove(market.id);
      return;
    }

    final impliedOdds = chosenOutcome == 'over'
        ? double.tryParse(market.impliedOddsOver)
        : double.tryParse(market.impliedOddsUnder);

    ref.read(selectedStockProvider.notifier).insertOrUpdate(
          SelectedStockModel(
            marketId: market.id,
            marketName: market.stock.companyName ?? market.stock.symbol,
            chosenOutcome: chosenOutcome,
            odds: chosenOutcome == 'over'
                ? _getOdds(
                    market.oddsAOver,
                    market.oddsDOver,
                    market.oddsFOver,
                    impliedOdds: impliedOdds,
                  )
                : _getOdds(
                    market.oddsAUnder,
                    market.oddsDUnder,
                    market.oddsFUnder,
                    impliedOdds: impliedOdds,
                  ),
            decimalOdds:
                chosenOutcome == 'over' ? market.oddsDOver : market.oddsDUnder,
            companyName: market.stock.companyName ?? market.stock.symbol,
            companySymbol: market.stock.symbol,
            logoUrl: market.stock.logoUrl ?? '',
            targetPrice: market.targetPrice,
            expiryDate: market.expiryDate,
          ),
        );
  }

  MarketModel _displayedMarket(MarketModel market) {
    return _marketOverrides[market.id] ?? market;
  }

  SelectedStockModel _buildSelectionFromMarket(
    MarketModel market,
    String chosenOutcome,
  ) {
    final impliedOdds = chosenOutcome == 'over'
        ? double.tryParse(market.impliedOddsOver)
        : double.tryParse(market.impliedOddsUnder);

    return SelectedStockModel(
      marketId: market.id,
      marketName: market.stock.companyName ?? market.stock.symbol,
      chosenOutcome: chosenOutcome,
      odds: chosenOutcome == 'over'
          ? _getOdds(
              market.oddsAOver,
              market.oddsDOver,
              market.oddsFOver,
              impliedOdds: impliedOdds,
            )
          : _getOdds(
              market.oddsAUnder,
              market.oddsDUnder,
              market.oddsFUnder,
              impliedOdds: impliedOdds,
            ),
      decimalOdds:
          chosenOutcome == 'over' ? market.oddsDOver : market.oddsDUnder,
      companyName: market.stock.companyName ?? market.stock.symbol,
      companySymbol: market.stock.symbol,
      logoUrl: market.stock.logoUrl ?? '',
      targetPrice: market.targetPrice,
      expiryDate: market.expiryDate,
    );
  }

  String _expiryQueryValue(String expiryDate) {
    final parsedIso = DateTime.tryParse(expiryDate);
    if (parsedIso != null) {
      return DateFormat('yyyy-MM-dd').format(parsedIso);
    }

    try {
      final parsedPretty = DateFormat('EEE, dd MMM yyyy').parse(expiryDate);
      return DateFormat('yyyy-MM-dd').format(parsedPretty);
    } catch (_) {
      return expiryDate;
    }
  }

  String _formatExpiryOption(String expiryDate) {
    final parsed = DateTime.tryParse(expiryDate);
    if (parsed == null) {
      return expiryDate;
    }

    return DateFormat('MMM d, yyyy').format(parsed);
  }

  Future<List<String>> _fetchExpiryOptions(String symbol) async {
    final response = await http.get(
      Uri.parse('https://api.bbbprediction.com/bet/expiries/?symbol=$symbol'),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to load expiries');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return List<String>.from(data['expiries'] ?? const <String>[]);
  }

  Future<List<MarketModel>> _fetchStrikeMarkets(
    String symbol,
    String expiry,
  ) async {
    final response = await http.get(
      Uri.parse(
        'https://api.bbbprediction.com/bet/markets/?search=$symbol&expiry=$expiry',
      ),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to load strike prices');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final results = (data['results'] as List<dynamic>? ?? const <dynamic>[])
        .map((item) => MarketModel.fromJson(item as Map<String, dynamic>))
        .toList()
      ..sort((a, b) => a.targetPrice.compareTo(b.targetPrice));

    final seenPrices = <String>{};

    return results.where((market) {
      final key = market.targetPrice.toStringAsFixed(2);
      if (seenPrices.contains(key)) {
        return false;
      }

      seenPrices.add(key);
      return true;
    }).toList();
  }

  Future<void> _replaceMarketInPlace(
    MarketModel originalMarket,
    MarketModel updatedMarket,
  ) async {
    final currentMarket = _displayedMarket(originalMarket);
    final selectedStocks = ref.read(selectedStockProvider);
    SelectedStockModel? currentSelection;

    for (final stock in selectedStocks) {
      if (stock.marketId == currentMarket.id) {
        currentSelection = stock;
        break;
      }
    }

    setState(() {
      _marketOverrides[originalMarket.id] = updatedMarket;
    });

    if (currentSelection != null) {
      ref
          .read(selectedStockProvider.notifier)
          .remove(currentSelection.marketId);
      ref.read(selectedStockProvider.notifier).insertOrUpdate(
            _buildSelectionFromMarket(
                updatedMarket, currentSelection.chosenOutcome),
          );
    }
  }

  Future<void> _showExpiryDialog(MarketModel originalMarket) async {
    try {
      final expiryOptions =
          await _fetchExpiryOptions(originalMarket.stock.symbol);

      if (!mounted || expiryOptions.isEmpty) {
        return;
      }

      final activeMarket = _displayedMarket(originalMarket);
      final currentExpiry = _expiryQueryValue(activeMarket.expiryDate);

      await showDialog<void>(
        context: context,
        barrierDismissible: true,
        builder: (dialogContext) {
          return Dialog(
            backgroundColor: const Color(0xFF1F242C),
            insetPadding:
                const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560, maxHeight: 520),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Select Expiry Date',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Expanded(
                      child: ListView.separated(
                        itemCount: expiryOptions.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (context, index) {
                          final expiry = expiryOptions[index];
                          final isSelected = expiry == currentExpiry;

                          return ListTile(
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                              side: BorderSide(
                                color: isSelected
                                    ? Colors.white
                                    : const Color(0xFF30363D),
                              ),
                            ),
                            tileColor: isSelected
                                ? Colors.white.withValues(alpha: 0.08)
                                : const Color(0xFF11151D),
                            title: Text(
                              _formatExpiryOption(expiry),
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            trailing: const Icon(
                              Icons.chevron_right_rounded,
                              color: Colors.white70,
                            ),
                            onTap: () async {
                              Navigator.of(dialogContext).pop();
                              await _showStrikeDialog(
                                originalMarket,
                                expiry: expiry,
                              );
                            },
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('We could not load expiry options right now.'),
        ),
      );
    }
  }

  Future<void> _showStrikeDialog(
    MarketModel originalMarket, {
    String? expiry,
  }) async {
    final activeMarket = _displayedMarket(originalMarket);
    final selectedExpiry = expiry ?? _expiryQueryValue(activeMarket.expiryDate);

    try {
      final strikeMarkets = await _fetchStrikeMarkets(
        activeMarket.stock.symbol,
        selectedExpiry,
      );

      if (!mounted || strikeMarkets.isEmpty) {
        return;
      }

      await showDialog<void>(
        context: context,
        barrierDismissible: true,
        builder: (dialogContext) {
          return Dialog(
            backgroundColor: const Color(0xFF1F242C),
            insetPadding:
                const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 620, maxHeight: 560),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Select Strike Price',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _formatExpiryOption(selectedExpiry),
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Expanded(
                      child: ListView.separated(
                        itemCount: strikeMarkets.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (context, index) {
                          final market = strikeMarkets[index];
                          final isSelected = market.id == activeMarket.id;

                          return ListTile(
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                              side: BorderSide(
                                color: isSelected
                                    ? Colors.white
                                    : const Color(0xFF30363D),
                              ),
                            ),
                            tileColor: isSelected
                                ? Colors.white.withValues(alpha: 0.08)
                                : const Color(0xFF11151D),
                            title: Text(
                              '\$${market.targetPrice.toStringAsFixed(2)}',
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            subtitle: Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: Row(
                                children: [
                                  _StrikeOddsPill(
                                    label: 'Over',
                                    odds: _getOdds(
                                      market.oddsAOver,
                                      market.oddsDOver,
                                      market.oddsFOver,
                                      impliedOdds: double.tryParse(
                                        market.impliedOddsOver,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  _StrikeOddsPill(
                                    label: 'Under',
                                    odds: _getOdds(
                                      market.oddsAUnder,
                                      market.oddsDUnder,
                                      market.oddsFUnder,
                                      impliedOdds: double.tryParse(
                                        market.impliedOddsUnder,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            onTap: () async {
                              Navigator.of(dialogContext).pop();
                              await _replaceMarketInPlace(
                                  originalMarket, market);
                            },
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('We could not load strike prices right now.'),
        ),
      );
    }
  }

  void _openStockProfile(BuildContext context, MarketModel market) {
    final currentUri = GoRouterState.of(context).uri;
    final competitionId = currentUri.queryParameters['competitionId'];
    final route = competitionId == null || competitionId.isEmpty
        ? '${DashboardRoutes.stockProfile}?id=${market.id}'
        : '${DashboardRoutes.stockProfile}?id=${market.id}&competitionId=$competitionId';
    context.go(route);
  }

  String _getOdds(String? a, String? d, String? f, {double? impliedOdds}) {
    switch (_preferredOdds) {
      case 'A':
        return a ?? 'N/A';
      case 'F':
        return f ?? 'N/A';
      case 'P':
        if (impliedOdds != null && impliedOdds > 0) {
          return '${(impliedOdds * 100).toStringAsFixed(2)}%';
        }
        return d ?? 'N/A';
      case 'D':
      default:
        return d ?? 'N/A';
    }
  }

  String _formatExpiry(String expiryDate) {
    final cleaned = expiryDate.replaceAll(',', '');
    final pieces = cleaned.split(' ');
    if (pieces.length >= 4) {
      return '${pieces[1]} ${pieces[2]}, ${pieces[3]}';
    }
    return expiryDate;
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final state = ref.watch(getMarketsProviderNew);
    final currentPath = GoRouterState.of(context).uri.path;
    final isCurrent = currentPath == widget.path;

    if (!isCurrent) {
      _didFetchForThisActivation = false;
    } else if (_prefsLoaded && !_didFetchForThisActivation) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || GoRouterState.of(context).uri.path != widget.path) {
          return;
        }
        _didFetchForThisActivation = true;
        _refreshForActivation();
      });
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: colors.always30363D),
            gradient: LinearGradient(
              colors: [
                colors.always30363D.withValues(alpha: 0.28),
                colors.primary.withValues(alpha: 0.96),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.title,
                style: TextStyle(
                  color: colors.alwaysWhite,
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                widget.subtitle,
                style: TextStyle(
                  color: colors.alwaysWhite.withValues(alpha: 0.7),
                  fontSize: 14,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Expanded(
          child: _isActivationLoading || state is LoadingState
              ? const Center(child: LoadingMainCard())
              : state is ErrorState
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 24),
                        child: Text(
                          'We could not load this market list right now.\n${state.errorMessage}',
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: Colors.white70,
                            height: 1.4,
                          ),
                        ),
                      ),
                    )
                  : state is SuccessState<PaginatedMarketModel>
                      ? Column(
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: Row(
                                children: [
                                  Text(
                                    '${state.data.totalCount} live contracts',
                                    style: TextStyle(
                                      color: colors.alwaysWhite
                                          .withValues(alpha: 0.7),
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  const Spacer(),
                                  Text(
                                    'Page $_currentPage of ${state.data.totalPages == 0 ? 1 : state.data.totalPages}',
                                    style: TextStyle(
                                      color: colors.alwaysWhite
                                          .withValues(alpha: 0.55),
                                      fontSize: 12,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Expanded(
                              child: Scrollbar(
                                controller: _scrollController,
                                thumbVisibility: true,
                                radius: const Radius.circular(99),
                                child: ListView.separated(
                                  controller: _scrollController,
                                  padding: const EdgeInsets.only(bottom: 16),
                                  itemCount: state.data.results.length,
                                  separatorBuilder: (_, __) =>
                                      const SizedBox(height: 14),
                                  itemBuilder: (context, index) {
                                    final market = state.data.results[index];
                                    final displayedMarket =
                                        _displayedMarket(market);
                                    final selectedStocks =
                                        ref.watch(selectedStockProvider);
                                    final isOverSelected = selectedStocks.any(
                                      (stock) =>
                                          stock.marketId ==
                                              displayedMarket.id &&
                                          stock.chosenOutcome == 'over',
                                    );
                                    final isUnderSelected = selectedStocks.any(
                                      (stock) =>
                                          stock.marketId ==
                                              displayedMarket.id &&
                                          stock.chosenOutcome == 'under',
                                    );

                                    return _MobileMarketCard(
                                      market: displayedMarket,
                                      expiryLabel: _formatExpiry(
                                          displayedMarket.expiryDate),
                                      overOdds: _getOdds(
                                        displayedMarket.oddsAOver,
                                        displayedMarket.oddsDOver,
                                        displayedMarket.oddsFOver,
                                        impliedOdds: double.tryParse(
                                          displayedMarket.impliedOddsOver,
                                        ),
                                      ),
                                      underOdds: _getOdds(
                                        displayedMarket.oddsAUnder,
                                        displayedMarket.oddsDUnder,
                                        displayedMarket.oddsFUnder,
                                        impliedOdds: double.tryParse(
                                          displayedMarket.impliedOddsUnder,
                                        ),
                                      ),
                                      isOverSelected: isOverSelected,
                                      isUnderSelected: isUnderSelected,
                                      onTapHeader: () => _openStockProfile(
                                          context, displayedMarket),
                                      onTapExpiry: () =>
                                          _showExpiryDialog(market),
                                      onTapStrike: () =>
                                          _showStrikeDialog(market),
                                      onTapOver: () => _toggleSelection(
                                          displayedMarket, 'over'),
                                      onTapUnder: () => _toggleSelection(
                                          displayedMarket, 'under'),
                                    );
                                  },
                                ),
                              ),
                            ),
                            if (state.data.totalPages > 1) ...[
                              const SizedBox(height: 10),
                              SingleChildScrollView(
                                scrollDirection: Axis.horizontal,
                                child: Row(
                                  children: List.generate(
                                    state.data.totalPages,
                                    (index) {
                                      final page = index + 1;
                                      final isActive =
                                          page.toString() == _currentPage;
                                      return Padding(
                                        padding: EdgeInsets.only(
                                          right: page == state.data.totalPages
                                              ? 0
                                              : 8,
                                        ),
                                        child: GestureDetector(
                                          onTap: () => _goToPage(page),
                                          child: AnimatedContainer(
                                            duration: const Duration(
                                                milliseconds: 180),
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 18,
                                              vertical: 12,
                                            ),
                                            decoration: BoxDecoration(
                                              borderRadius:
                                                  BorderRadius.circular(18),
                                              color: isActive
                                                  ? colors.alwaysWhite
                                                  : colors.always30363D
                                                      .withValues(alpha: 0.34),
                                              border: Border.all(
                                                color: isActive
                                                    ? colors.alwaysWhite
                                                    : colors.alwaysWhite
                                                        .withValues(alpha: 0.2),
                                              ),
                                            ),
                                            child: Text(
                                              '$page',
                                              style: TextStyle(
                                                color: isActive
                                                    ? colors.primary
                                                    : colors.alwaysWhite,
                                                fontSize: 13,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                                ),
                              ),
                            ],
                          ],
                        )
                      : const Center(child: LoadingMainCard()),
        ),
      ],
    );
  }
}

class _MobileMarketCard extends StatelessWidget {
  const _MobileMarketCard({
    required this.market,
    required this.expiryLabel,
    required this.overOdds,
    required this.underOdds,
    required this.isOverSelected,
    required this.isUnderSelected,
    required this.onTapHeader,
    required this.onTapExpiry,
    required this.onTapStrike,
    required this.onTapOver,
    required this.onTapUnder,
  });

  final MarketModel market;
  final String expiryLabel;
  final String overOdds;
  final String underOdds;
  final bool isOverSelected;
  final bool isUnderSelected;
  final VoidCallback onTapHeader;
  final VoidCallback onTapExpiry;
  final VoidCallback onTapStrike;
  final VoidCallback onTapOver;
  final VoidCallback onTapUnder;

  @override
  Widget build(BuildContext context) {
    return Consumer(
      builder: (context, ref, _) {
        final colors = ref.watch(appThemeProvider).colors;
        final companyName = market.stock.companyName ?? market.stock.symbol;

        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: colors.always30363D),
            color: const Color(0xFF11151D),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.16),
                blurRadius: 18,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: onTapHeader,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _StockLogo(
                      symbol: market.stock.symbol,
                      logoUrl: market.stock.logoUrl,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            companyName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: colors.alwaysWhite,
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '\$${market.stock.symbol}',
                            style: TextStyle(
                              color: colors.alwaysWhite.withValues(alpha: 0.6),
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Icon(
                      Icons.chevron_right_rounded,
                      color: colors.alwaysWhite.withValues(alpha: 0.45),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _InfoPill(
                    icon: Icons.event_outlined,
                    label: expiryLabel,
                    onTap: onTapExpiry,
                    isInteractive: true,
                  ),
                  _InfoPill(
                    iconAsset: Pngs.strikePrice,
                    label: '\$${market.targetPrice.toStringAsFixed(2)} strike',
                    onTap: onTapStrike,
                    isInteractive: true,
                  ),
                  if (market.lastPrice != null)
                    _InfoPill(
                      icon: Icons.show_chart_rounded,
                      label: 'Last \$${market.lastPrice!.toStringAsFixed(2)}',
                    ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: _OutcomeButton(
                      title: 'Over',
                      odds: overOdds,
                      selected: isOverSelected,
                      onTap: onTapOver,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _OutcomeButton(
                      title: 'Under',
                      odds: underOdds,
                      selected: isUnderSelected,
                      onTap: onTapUnder,
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _StockLogo extends StatelessWidget {
  const _StockLogo({
    required this.symbol,
    required this.logoUrl,
  });

  final String symbol;
  final String? logoUrl;

  @override
  Widget build(BuildContext context) {
    if (logoUrl != null && logoUrl!.isNotEmpty) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Image.network(
          logoUrl!,
          width: 44,
          height: 44,
          fit: BoxFit.cover,
        ),
      );
    }

    return Container(
      width: 44,
      height: 44,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: Colors.white,
      ),
      child: Text(
        symbol.substring(0, symbol.length >= 2 ? 2 : 1).toUpperCase(),
        style: const TextStyle(
          color: Colors.black,
          fontWeight: FontWeight.w800,
          fontSize: 14,
        ),
      ),
    );
  }
}

class _InfoPill extends ConsumerWidget {
  const _InfoPill({
    required this.label,
    this.icon,
    this.iconAsset,
    this.onTap,
    this.isInteractive = false,
  });

  final String label;
  final IconData? icon;
  final String? iconAsset;
  final VoidCallback? onTap;
  final bool isInteractive;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: colors.always30363D.withValues(alpha: 0.32),
          border: Border.all(color: colors.always30363D),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null)
              Icon(icon,
                  size: 14, color: colors.alwaysWhite.withValues(alpha: 0.72)),
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
                color: colors.alwaysWhite.withValues(alpha: 0.92),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (isInteractive) ...[
              const SizedBox(width: 8),
              Icon(
                Icons.edit_outlined,
                size: 14,
                color: colors.alwaysWhite.withValues(alpha: 0.72),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _OutcomeButton extends ConsumerWidget {
  const _OutcomeButton({
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
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: selected
              ? colors.alwaysWhite
              : colors.always30363D.withValues(alpha: 0.24),
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
                color: selected
                    ? colors.primary
                    : colors.alwaysWhite.withValues(alpha: 0.72),
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              odds,
              style: TextStyle(
                color: selected ? colors.primary : colors.alwaysWhite,
                fontSize: 18,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StrikeOddsPill extends StatelessWidget {
  const _StrikeOddsPill({
    required this.label,
    required this.odds,
  });

  final String label;
  final String odds;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: Colors.white.withValues(alpha: 0.06),
        border: Border.all(color: const Color(0xFF30363D)),
      ),
      child: Text(
        '$label $odds',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
