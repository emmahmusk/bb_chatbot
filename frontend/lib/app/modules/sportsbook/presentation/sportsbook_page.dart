import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/app/shared/classes/http/http.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:go_router/go_router.dart';

import '../data/sportsbook_models.dart';
import '../data/sportsbook_repository.dart';

class SportsbookPage extends ConsumerStatefulWidget {
  const SportsbookPage({super.key});

  @override
  ConsumerState<SportsbookPage> createState() => _SportsbookPageState();
}

class _SportsbookPageState extends ConsumerState<SportsbookPage> {
  late final SportsbookRepository _repository;
  List<SportsbookSport> _sports = [];
  List<SportsbookProvider> _providers = [];
  List<SportsbookLeague> _leagues = [];
  List<SportsbookFixture> _fixtures = [];
  final Map<String, List<SportsbookOdd>> _oddsByFixture = {};
  final Map<String, bool> _loadingOdds = {};
  final Map<String, SportsbookSelection> _slip = {};
  String? _sport;
  String? _league;
  String? _fixtureFilter;
  String _market = 'moneyline';
  String _error = '';
  String _status = 'Choose a sport to start';
  bool _loading = true;
  bool _placing = false;
  final TextEditingController _stakeController = TextEditingController(text: '100');

  @override
  void initState() {
    super.initState();
    _repository = SportsbookRepository(ref.read(httpProvider));
    _bootstrap();
  }

  @override
  void dispose() {
    _stakeController.dispose();
    super.dispose();
  }

  Future<void> _bootstrap() async {
    try {
      final result = await _repository.catalog();
      if (!mounted) return;
      setState(() { _sports = result.$1; _providers = result.$2; _loading = false; });
      if (_sports.isNotEmpty) await _selectSport(_sports.first.id);
    } catch (error) {
      if (mounted) setState(() { _loading = false; _error = error.toString().replaceFirst('Exception: ', ''); });
    }
  }

  Future<void> _selectSport(String? sport) async {
    if (sport == null || sport.isEmpty) return;
    setState(() { _sport = sport; _league = null; _fixtureFilter = null; _leagues = []; _fixtures = []; _status = 'Loading leagues…'; _error = ''; });
    try {
      final leagues = await _repository.leagues(sport);
      if (!mounted) return;
      setState(() { _leagues = leagues; _status = leagues.isEmpty ? 'No active leagues' : 'Choose a league'; });
    } catch (error) { if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', '')); }
  }

  Future<void> _selectLeague(String? league) async {
    if (league == null || league.isEmpty || _sport == null) return;
    setState(() { _league = league; _fixtureFilter = null; _fixtures = []; _oddsByFixture.clear(); _status = 'Loading upcoming fixtures…'; _error = ''; });
    try {
      final fixtures = await _repository.fixtures(_sport!, league);
      fixtures.sort((a, b) { if (a.isLive != b.isLive) return a.isLive ? -1 : 1; return (a.startDate ?? DateTime(9999)).compareTo(b.startDate ?? DateTime(9999)); });
      if (!mounted) return;
      setState(() { _fixtures = fixtures; _status = fixtures.isEmpty ? 'No upcoming fixtures' : '${fixtures.length} fixtures available'; });
      for (final fixture in fixtures.take(5)) { _loadOdds(fixture); }
    } catch (error) { if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', '')); }
  }

  Future<void> _loadOdds(SportsbookFixture fixture) async {
    if (_oddsByFixture.containsKey(fixture.id) || _loadingOdds[fixture.id] == true) return;
    setState(() => _loadingOdds[fixture.id] = true);
    try {
      final odds = await _repository.odds(fixture.id, _market, _providers);
      if (mounted) setState(() => _oddsByFixture[fixture.id] = odds);
    } catch (error) { if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', '')); }
    finally { if (mounted) setState(() => _loadingOdds[fixture.id] = false); }
  }

  void _toggleSelection(SportsbookFixture fixture, SportsbookOdd odd, List<SportsbookOdd> snapshot) {
    final selection = SportsbookSelection(draftKings: odd, snapshot: snapshot);
    setState(() { if (_slip.containsKey(fixture.id)) { _slip.remove(fixture.id); } else { _slip[fixture.id] = selection; } });
  }

  double get _combinedOdds => _slip.values.fold(1, (value, selection) => value * selection.draftKings.decimal);
  double get _stake => double.tryParse(_stakeController.text.replaceAll(',', '')) ?? 0;
  double get _potentialPayout => _stake * _combinedOdds;
  List<SportsbookFixture> get _visibleFixtures => _fixtureFilter == null ? _fixtures.take(5).toList() : _fixtures.where((fixture) => fixture.id == _fixtureFilter).toList();

  Future<void> _placeBetslip() async {
    if (_slip.isEmpty || _stake <= 0) return;
    if (ref.read(currentUserProvider) == null) {
      setState(() => _error = '');
      showCenterDialog(context, child: const LoginDialog());
      return;
    }
    setState(() { _placing = true; _error = ''; });
    try {
      final body = await _repository.recordBetSlip(stake: _stake, selections: _slip.values.toList());
      if (!mounted) return;
      setState(() { _slip.clear(); _placing = false; });
      _showMessage('Bet recorded · ${body['leg_count']} leg(s) · potential payout ${body['potential_payout']}');
    } catch (error) { if (mounted) setState(() { _placing = false; _error = error.toString().replaceFirst('Exception: ', ''); }); }
  }

  void _showMessage(String message) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final requiresLogin = ref.watch(currentUserProvider) == null;
    return Scaffold(backgroundColor: colors.primary, body: SafeArea(child: LayoutBuilder(builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1050;
      return Column(children: [
        _buildHeader(colors),
        Expanded(child: SingleChildScrollView(padding: EdgeInsets.symmetric(horizontal: wide ? 52 : 16, vertical: 24), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (requiresLogin) _loginRequiredNotice(colors),
          if (requiresLogin) const SizedBox(height: 14),
          _buildIntro(colors),
          const SizedBox(height: 22),
          if (wide) Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Expanded(child: _buildMain(colors)), const SizedBox(width: 20), SizedBox(width: 360, child: _buildSlip(colors))]) else Column(children: [_buildMain(colors), const SizedBox(height: 18), _buildSlip(colors)]),
          if (_error.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 14), child: _errorCard(colors)),
        ]))),
      ]);
    })));
  }

  Widget _buildHeader(dynamic colors) => Padding(padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 12), child: Row(children: [IconButton(onPressed: () => context.go('/dashboard/trending'), icon: Icon(Icons.arrow_back_rounded, color: colors.alwaysWhite)), const SizedBox(width: 8), Text('ODDS LAB', style: TextStyle(color: colors.alwaysWhite, fontWeight: FontWeight.w700, letterSpacing: 3)), const Spacer(), Container(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9), decoration: BoxDecoration(border: Border.all(color: colors.always30363D), borderRadius: BorderRadius.circular(22)), child: Row(children: [Icon(Icons.circle, size: 8, color: colors.always27D07F), const SizedBox(width: 8), Text('Sportsbook feed', style: TextStyle(color: colors.alwaysE6EDF3, fontSize: 12))]))]));
  Widget _loginRequiredNotice(dynamic colors) => Container(width: double.infinity, padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14), decoration: BoxDecoration(color: colors.always1F242C, border: Border.all(color: colors.alwaysFF4C4C.withOpacity(.65)), borderRadius: BorderRadius.circular(13)), child: Row(children: [Icon(Icons.lock_outline_rounded, color: colors.alwaysFF4C4C, size: 20), const SizedBox(width: 12), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('Log in before placing a sportsbook bet', style: TextStyle(color: colors.alwaysWhite, fontSize: 13, fontWeight: FontWeight.w700)), const SizedBox(height: 3), Text('You can browse the available lines now. Sign in when you are ready to add a selection to your bet slip.', style: TextStyle(color: colors.alwaysE6EDF3, fontSize: 10, height: 1.4))])), TextButton(onPressed: () => showCenterDialog(context, child: const LoginDialog()), child: Text('Log in', style: TextStyle(color: colors.alwaysWhite, fontWeight: FontWeight.w700, fontSize: 12)))]));
  Widget _buildIntro(dynamic colors) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('SPORTSBOOK', style: TextStyle(color: colors.always27D07F, letterSpacing: 3, fontSize: 11, fontWeight: FontWeight.w700)), const SizedBox(height: 10), Text('Shop the line.\nBet with context.', style: TextStyle(color: colors.alwaysWhite, fontSize: 34, height: 1.05, fontWeight: FontWeight.w700)), const SizedBox(height: 10), Text('DraftKings is the betting line. Comparison books are checked automatically in the monitoring panel after placement.', style: TextStyle(color: colors.always8B949E, fontSize: 13, height: 1.5))]);

  Widget _buildMain(dynamic colors) => Container(padding: const EdgeInsets.all(18), decoration: BoxDecoration(color: colors.always161B22, border: Border.all(color: colors.always30363D), borderRadius: BorderRadius.circular(18)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(children: [Expanded(child: _dropdown<SportsbookSport>(label: 'Sport', value: _sport, items: _sports, getValue: (item) => item.id, getLabel: (item) => item.name, onChanged: _selectSport)), const SizedBox(width: 10), Expanded(child: _dropdown<SportsbookLeague>(label: 'League', value: _league, items: _leagues, getValue: (item) => item.id, getLabel: (item) => item.name, onChanged: _selectLeague))]), const SizedBox(height: 12), if (_fixtures.isNotEmpty) _fixtureDropdown(colors), if (_fixtures.isNotEmpty) const SizedBox(height: 12), Row(children: [Expanded(child: _dropdown<String>(label: 'Market', value: _market, items: const ['moneyline', 'point_spread', 'total_points'], getValue: (item) => item, getLabel: (item) => _pretty(item), onChanged: (value) { if (value != null) { setState(() => _market = value); for (final fixture in _visibleFixtures) { _oddsByFixture.remove(fixture.id); _loadOdds(fixture); } } })), const SizedBox(width: 10), Expanded(child: Align(alignment: Alignment.bottomRight, child: Text(_status, style: TextStyle(color: colors.always8B949E, fontSize: 11))))]), const SizedBox(height: 18), if (_loading) const Center(child: Padding(padding: EdgeInsets.all(28), child: CircularProgressIndicator())) else if (_fixtures.isEmpty) _emptyState(colors, _league == null ? 'Choose a sport and league' : 'No upcoming fixtures found') else ..._visibleFixtures.map((fixture) => _fixtureCard(colors, fixture))]));

  Widget _fixtureDropdown(dynamic colors) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('Fixture', style: TextStyle(color: colors.always8B949E, fontSize: 11)), const SizedBox(height: 6), DropdownButtonFormField<String>(value: _fixtureFilter ?? '', isExpanded: true, dropdownColor: colors.always1F242C, style: TextStyle(color: colors.alwaysWhite, fontSize: 12), decoration: InputDecoration(filled: true, fillColor: colors.always0D1117, border: OutlineInputBorder(borderRadius: BorderRadius.circular(11), borderSide: BorderSide(color: colors.always30363D)), contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10)), items: [const DropdownMenuItem<String>(value: '', child: Text('First five upcoming fixtures')), ..._fixtures.map((fixture) => DropdownMenuItem<String>(value: fixture.id, child: Text(fixture.event.isEmpty ? fixture.id : fixture.event, overflow: TextOverflow.ellipsis)))], onChanged: (value) { final selected = value == null || value.isEmpty ? null : value; setState(() => _fixtureFilter = selected); if (selected != null) { final fixture = _fixtures.firstWhere((item) => item.id == selected); _loadOdds(fixture); } })]);

  Widget _dropdown<T>({required String label, required String? value, required List<T> items, required String Function(T) getValue, required String Function(T) getLabel, required ValueChanged<String?> onChanged}) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label, style: const TextStyle(color: Color(0xFF8B949E), fontSize: 11)), const SizedBox(height: 6), DropdownButtonFormField<String>(value: value, isExpanded: true, dropdownColor: const Color(0xFF1F242C), style: const TextStyle(color: Colors.white, fontSize: 12), decoration: InputDecoration(filled: true, fillColor: const Color(0xFF0D1117), border: OutlineInputBorder(borderRadius: BorderRadius.circular(11), borderSide: const BorderSide(color: Color(0xFF30363D))), contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10)), hint: Text('Choose $label', style: const TextStyle(color: Color(0xFF6E7681), fontSize: 12)), items: items.map((item) => DropdownMenuItem<String>(value: getValue(item), child: Text(getLabel(item), overflow: TextOverflow.ellipsis))).toList(), onChanged: onChanged)]);

  Widget _fixtureCard(dynamic colors, SportsbookFixture fixture) { final odds = _oddsByFixture[fixture.id] ?? []; final grouped = <String, List<SportsbookOdd>>{}; for (final odd in odds) { grouped.putIfAbsent(odd.selection, () => []).add(odd); } final ordered = grouped.entries.toList()..sort((a, b) => _outcomeRank(a.key, fixture).compareTo(_outcomeRank(b.key, fixture))); return Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: colors.always0D1117, border: Border.all(color: colors.always30363D), borderRadius: BorderRadius.circular(14)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(children: [Expanded(child: Text(fixture.event, style: TextStyle(color: colors.alwaysWhite, fontWeight: FontWeight.w600, fontSize: 14))), Text(fixture.isLive ? 'LIVE' : _dateLabel(fixture.startDate), style: TextStyle(color: fixture.isLive ? colors.always27D07F : colors.always8B949E, fontSize: 10, fontWeight: FontWeight.w700))]), const SizedBox(height: 12), if (_loadingOdds[fixture.id] == true) const LinearProgressIndicator(minHeight: 2) else if (grouped.isEmpty) Text('No DraftKings moneyline currently available.', style: TextStyle(color: colors.always8B949E, fontSize: 11)) else ...ordered.map((entry) => _outcomeRow(colors, fixture, entry.key, entry.value)),])); }

  int _outcomeRank(String selection, SportsbookFixture fixture) { final key = selection.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), ''); final home = fixture.homeTeam.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), ''); final away = fixture.awayTeam.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), ''); if (key == 'draw' || key == 'tie' || key == 'x') return 1; if (key == '1' || key == 'home' || (home.isNotEmpty && (key == home || key.contains(home) || home.contains(key)))) return 0; if (key == '2' || key == 'away' || (away.isNotEmpty && (key == away || key.contains(away) || away.contains(key)))) return 2; return 3; }

  Widget _outcomeRow(dynamic colors, SportsbookFixture fixture, String selection, List<SportsbookOdd> lines) {
    final draftKingsLines = lines.where((odd) => odd.sportsbook == 'draftkings').toList();
    // DraftKings is the baseline. Never make a peer look like the baseline
    // when the DraftKings quote is temporarily unavailable.
    if (draftKingsLines.isEmpty) return const SizedBox.shrink();
    final draftKings = draftKingsLines.first;
    final selected = _slip.containsKey(fixture.id) && _slip[fixture.id]!.draftKings.selection == selection;
    final peers = lines.where((odd) => odd.sportsbook != 'draftkings').take(3).toList();
    Widget priceBlock() => Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
      Text(draftKings.decimal.toStringAsFixed(2), style: TextStyle(color: colors.alwaysWhite, fontWeight: FontWeight.w700, fontSize: 16)),
      Text('DK  ${draftKings.price}', style: TextStyle(color: colors.always8B949E, fontSize: 9)),
    ]);
    Widget peerBlock() => Wrap(spacing: 10, runSpacing: 4, children: peers.map((odd) => Text('${odd.sportsbook.toUpperCase()} ${odd.decimal.toStringAsFixed(2)}', style: TextStyle(color: colors.always8B949E, fontSize: 10))).toList());
    return Padding(
      padding: const EdgeInsets.only(top: 7),
      child: InkWell(
        onTap: () => _toggleSelection(fixture, draftKings, _oddsByFixture[fixture.id]!.where((odd) => odd.selection == selection).toList()),
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(color: selected ? colors.always003D2E : colors.always1F242C, border: Border.all(color: selected ? colors.always27D07F : colors.always30363D), borderRadius: BorderRadius.circular(10)),
          child: LayoutBuilder(builder: (context, constraints) {
            final addIcon = selected ? Icon(Icons.check_circle, color: colors.always27D07F, size: 18) : Icon(Icons.add_circle_outline, color: colors.always8B949E, size: 18);
            if (constraints.maxWidth < 520) {
              return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [Expanded(child: Text(selection, style: TextStyle(color: colors.alwaysWhite, fontWeight: FontWeight.w600, fontSize: 12))), priceBlock(), const SizedBox(width: 8), addIcon]),
                if (peers.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 7), child: peerBlock()),
              ]);
            }
            return Row(children: [Expanded(child: Text(selection, style: TextStyle(color: colors.alwaysWhite, fontWeight: FontWeight.w600, fontSize: 12))), priceBlock(), if (peers.isNotEmpty) Padding(padding: const EdgeInsets.only(left: 10), child: peerBlock()), const SizedBox(width: 8), addIcon]);
          }),
        ),
      ),
    );
  }

  Widget _buildSlip(dynamic colors) { final hasSelections = _slip.isNotEmpty; return Container(padding: const EdgeInsets.all(18), decoration: BoxDecoration(color: colors.always1F242C, border: Border.all(color: colors.always30363D), borderRadius: BorderRadius.circular(18)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(children: [Text('Bet slip', style: TextStyle(color: colors.alwaysWhite, fontWeight: FontWeight.w700, fontSize: 20)), const Spacer(), Text('${_slip.length} leg${_slip.length == 1 ? '' : 's'}', style: TextStyle(color: colors.always8B949E, fontSize: 11))]), const SizedBox(height: 12), if (!hasSelections) _emptyState(colors, 'Select DraftKings odds to build a parlay') else ...[..._slip.entries.map((entry) => _slipItem(colors, entry.key, entry.value)), const SizedBox(height: 12), TextField(controller: _stakeController, keyboardType: const TextInputType.numberWithOptions(decimal: true), onChanged: (_) => setState(() {}), style: TextStyle(color: colors.alwaysWhite), decoration: InputDecoration(labelText: 'Stake', prefixText: 'BBC ', labelStyle: TextStyle(color: colors.always8B949E), prefixStyle: TextStyle(color: colors.always8B949E), filled: true, fillColor: colors.always0D1117, border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: colors.always30363D)))), const SizedBox(height: 12), _summaryRow(colors, 'Combined odds', _combinedOdds.toStringAsFixed(2)), _summaryRow(colors, 'Potential payout', _potentialPayout.toStringAsFixed(2)), const SizedBox(height: 12), CustomButton(text: _placing ? 'Recording…' : 'Record bet', fontSize: 13, height: 48, onPressed: _placing ? null : _placeBetslip, validator: () => !_placing && _stake > 0), Text('This POC records the DraftKings selection and comparison snapshot; it does not place a live sportsbook wager.', style: TextStyle(color: colors.always6E7681, fontSize: 9, height: 1.4))]])); }

  Widget _slipItem(dynamic colors, String fixtureId, SportsbookSelection selection) => Padding(padding: const EdgeInsets.only(bottom: 8), child: Row(children: [Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(selection.draftKings.event, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: colors.always8B949E, fontSize: 10)), Text(selection.draftKings.selection, style: TextStyle(color: colors.alwaysWhite, fontSize: 12, fontWeight: FontWeight.w600))])), Column(crossAxisAlignment: CrossAxisAlignment.end, children: [Text(selection.draftKings.decimal.toStringAsFixed(2), style: TextStyle(color: colors.always27D07F, fontWeight: FontWeight.w700)), Text(selection.draftKings.price, style: TextStyle(color: colors.always8B949E, fontSize: 9))]), IconButton(onPressed: () => setState(() => _slip.remove(fixtureId)), icon: Icon(Icons.close, color: colors.always8B949E, size: 16), padding: EdgeInsets.zero, constraints: const BoxConstraints())]));
  Widget _summaryRow(dynamic colors, String label, String value) => Padding(padding: const EdgeInsets.symmetric(vertical: 3), child: Row(children: [Text(label, style: TextStyle(color: colors.always8B949E, fontSize: 11)), const Spacer(), Text(value, style: TextStyle(color: colors.alwaysWhite, fontWeight: FontWeight.w700, fontSize: 13))]));
  Widget _emptyState(dynamic colors, String message) => Padding(padding: const EdgeInsets.symmetric(vertical: 24), child: Center(child: Text(message, textAlign: TextAlign.center, style: TextStyle(color: colors.always8B949E, fontSize: 11))));
  Widget _errorCard(dynamic colors) => Container(width: double.infinity, padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: colors.alwaysFEF3F2.withOpacity(.08), border: Border.all(color: colors.alwaysFF4C4C.withOpacity(.5)), borderRadius: BorderRadius.circular(10)), child: Text(_error, style: TextStyle(color: colors.alwaysFF4C4C, fontSize: 11)));
  String _dateLabel(DateTime? value) => value == null ? 'Upcoming' : '${value.month}/${value.day} · ${value.hour == 0 ? 12 : (value.hour > 12 ? value.hour - 12 : value.hour)}:${value.minute.toString().padLeft(2, '0')} ${value.hour >= 12 ? 'PM' : 'AM'}';
  String _pretty(String value) => value.replaceAll('_', ' ').split(' ').map((word) => word.isEmpty ? word : '${word[0].toUpperCase()}${word.substring(1)}').join(' ');
}
