import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_checkbox.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/app/shared/providers/preferences_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum OddsType { decimal, american, fraction, probability }

class DesktopBettingPreferencePage extends ConsumerStatefulWidget {
  const DesktopBettingPreferencePage({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _DesktopBettingPreferencePageState();
}

class _DesktopBettingPreferencePageState
    extends ConsumerState<DesktopBettingPreferencePage> {
  OddsType _selectedType = OddsType.probability;

  @override
  void initState() {
    super.initState();
    _loadSelectedOddsType();
  }

  Future<void> _loadSelectedOddsType() async {
    final prefs = await SharedPreferences.getInstance();
    final storedOdds = prefs.getString('odds_type') ?? 'P';

    setState(() {
      switch (storedOdds) {
        case 'A':
          _selectedType = OddsType.american;
          break;
        case 'F':
          _selectedType = OddsType.fraction;
          break;
        case 'D':
          _selectedType = OddsType.decimal;
          break;
        case 'P':
        default:
          _selectedType = OddsType.probability;
      }
    });
  }

  Future<void> _selectOddsType(OddsType type, String storedValue) async {
    setState(() => _selectedType = type);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('odds_type', storedValue);
    ref.read(oddsTypeProvider.notifier).state = storedValue;
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final isCompact = MediaQuery.of(context).size.width < 600;

    Widget buildDesktopOption({
      required OddsType type,
      required String storedValue,
    }) {
      return SizedBox(
        width: 80,
        child: Center(
          child: CustomCheckbox(
            value: _selectedType == type,
            onTap: () => _selectOddsType(type, storedValue),
          ),
        ),
      );
    }

    Widget buildMobileOption({
      required String label,
      required OddsType type,
      required String storedValue,
    }) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: colors.always161B22,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.always30363D.withValues(alpha: 0.8)),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: colors.alwaysWhite,
                ),
              ),
            ),
            CustomCheckbox(
              value: _selectedType == type,
              onTap: () => _selectOddsType(type, storedValue),
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(24, 24, 24, isCompact ? 32 : 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Betting Preference',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: colors.alwaysWhite,
            ),
          ),
          const SizedBox(height: 44),
          Padding(
            padding: const EdgeInsets.only(bottom: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (isCompact) ...[
                  Text(
                    'Type',
                    style: TextStyle(
                      fontSize: 14,
                      color: colors.always8B949E,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: const [
                      _PreferenceTag(label: 'Decimal'),
                      _PreferenceTag(label: 'American'),
                      _PreferenceTag(label: 'Fraction'),
                      _PreferenceTag(label: 'Prob.'),
                    ],
                  ),
                ] else
                  Row(
                    children: [
                      Expanded(
                        child: Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            'Type',
                            style: TextStyle(
                              fontSize: 14,
                              color: colors.always8B949E,
                              fontWeight: FontWeight.w400,
                            ),
                          ),
                        ),
                      ),
                      const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          SizedBox(
                            width: 80,
                            child: Text(
                              'Decimal',
                              style: TextStyle(
                                fontSize: 14,
                                color: Color(0xFF9A9A9A),
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ),
                          SizedBox(
                            width: 80,
                            child: Text(
                              'American',
                              style: TextStyle(
                                fontSize: 14,
                                color: Color(0xFF9A9A9A),
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ),
                          SizedBox(
                            width: 80,
                            child: Text(
                              'Fraction',
                              style: TextStyle(
                                fontSize: 14,
                                color: Color(0xFF9A9A9A),
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ),
                          SizedBox(
                            width: 80,
                            child: Text(
                              'Prob.',
                              style: TextStyle(
                                fontSize: 14,
                                color: Color(0xFF9A9A9A),
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                const SizedBox(height: 29),
                const CustomDivider(),
                const SizedBox(height: 29),
                if (isCompact) ...[
                  Text(
                    'Odd Type',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      color: colors.alwaysWhite,
                    ),
                  ),
                  const SizedBox(height: 16),
                  buildMobileOption(
                    label: 'Decimal',
                    type: OddsType.decimal,
                    storedValue: 'D',
                  ),
                  const SizedBox(height: 12),
                  buildMobileOption(
                    label: 'American',
                    type: OddsType.american,
                    storedValue: 'A',
                  ),
                  const SizedBox(height: 12),
                  buildMobileOption(
                    label: 'Fraction',
                    type: OddsType.fraction,
                    storedValue: 'F',
                  ),
                  const SizedBox(height: 12),
                  buildMobileOption(
                    label: 'Probability',
                    type: OddsType.probability,
                    storedValue: 'P',
                  ),
                ] else
                  Row(
                    children: [
                      Expanded(
                        child: Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            'Odd Type',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                              color: colors.alwaysWhite,
                            ),
                          ),
                        ),
                      ),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          buildDesktopOption(
                            type: OddsType.decimal,
                            storedValue: 'D',
                          ),
                          buildDesktopOption(
                            type: OddsType.american,
                            storedValue: 'A',
                          ),
                          buildDesktopOption(
                            type: OddsType.fraction,
                            storedValue: 'F',
                          ),
                          buildDesktopOption(
                            type: OddsType.probability,
                            storedValue: 'P',
                          ),
                        ],
                      ),
                    ],
                  ),
                const SizedBox(height: 29),
                const CustomDivider(),
              ],
            ),
          ),
          const OddDescriptionText(
            title: 'Decimal Odd',
            subtitle:
                'The number represents the multiplier on return from wagered amounts. Ex. 1.91, 1.83, 2.05, 7.5',
          ),
          const SizedBox(height: 24),
          const OddDescriptionText(
            title: 'American Odd',
            subtitle:
                'American odds display a "+" or "-" in front of the number. "-" signifies the favorite while "+" represents the underdog.',
          ),
          const SizedBox(height: 24),
          const OddDescriptionText(
            title: 'Fraction Odd',
            subtitle:
                'Fraction odds compare profit to stake. Ex. 1/1 (50% or +100 or 2.00), 1/2, 1/3, 4/1, 6/1, 9/1.',
          ),
          const OddDescriptionText(
            title: 'Probability',
            subtitle:
                'Displays the probability of the outcome as a percentage. Ex. 50%, 33.33%, 66.67%, 85%',
          ),
        ],
      ),
    );
  }
}

class _PreferenceTag extends StatelessWidget {
  const _PreferenceTag({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFF30363D)),
        color: const Color(0xFF161B22),
      ),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 12,
          color: Color(0xFF9A9A9A),
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}

class OddDescriptionText extends ConsumerWidget {
  final String title;
  final String subtitle;

  const OddDescriptionText({
    super.key,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = ref.watch(appThemeProvider).colors;
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: colors.alwaysWhite,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: TextStyle(
              fontSize: 14,
              height: 1.5,
              fontWeight: FontWeight.w400,
              color: colors.always8B949E,
            ),
          ),
        ],
      ),
    );
  }
}
