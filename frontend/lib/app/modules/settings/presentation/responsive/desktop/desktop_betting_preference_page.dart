import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_checkbox.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_divider.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/app/shared/providers/preferences_provider.dart';

enum OddsType { decimal, american, fraction, probability }

class DesktopBettingPreferencePage extends ConsumerStatefulWidget {
  const DesktopBettingPreferencePage({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _DesktopBettingPreferencePageState();
}

class _DesktopBettingPreferencePageState
    extends ConsumerState<DesktopBettingPreferencePage> {
  OddsType _selectedType = OddsType.decimal;

@override
void initState() {
  super.initState();
  _loadSelectedOddsType();
}


Future<void> _loadSelectedOddsType() async {
  final prefs = await SharedPreferences.getInstance();
  final storedOdds = prefs.getString('odds_type') ?? 'D'; // default to Decimal

  setState(() {
    switch (storedOdds) {
      case 'A':
        _selectedType = OddsType.american;
        break;
      case 'F':
        _selectedType = OddsType.fraction;
        break;
      case 'P':
        _selectedType = OddsType.probability;
        break;
      case 'D':
      default:
        _selectedType = OddsType.decimal;
    }
  });
}

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;

    return SizedBox(
      height: MediaQuery.of(context).size.height,
      child: SingleChildScrollView(
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
                children: [
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
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: const [
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
                  CustomDivider(),
                  const SizedBox(height: 29),
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
                          SizedBox(
                            width: 80,
                            child: Center(
                              child: CustomCheckbox(
                                value: _selectedType == OddsType.decimal,
                                onTap: () async {
                                  setState(() => _selectedType = OddsType.decimal);
                                  final prefs = await SharedPreferences.getInstance();
                                  prefs.setString('odds_type', 'D');
                                  ref.read(oddsTypeProvider.notifier).state = 'D';
                                },
                              ),
                            ),
                          ),
                          SizedBox(
                            width: 80,
                            child: Center(
                              child: CustomCheckbox(
                                value: _selectedType == OddsType.american,
                                onTap: () async {
                                  setState(() => _selectedType = OddsType.american);
                                  final prefs = await SharedPreferences.getInstance();
                                  prefs.setString('odds_type', 'A');
                                  ref.read(oddsTypeProvider.notifier).state = 'A';
                                },
                              ),
                            ),
                          ),
                          SizedBox(
                            width: 80,
                            child: Center(
                              child: CustomCheckbox(
                                value: _selectedType == OddsType.fraction,
                                onTap: () async {
                                  setState(() => _selectedType = OddsType.fraction);
                                  final prefs = await SharedPreferences.getInstance();
                                  prefs.setString('odds_type', 'F');
                                  ref.read(oddsTypeProvider.notifier).state = 'F';
                                },
                              ),
                            ),
                          ),
                          SizedBox(
                            width: 80,
                            child: Center(
                              child: CustomCheckbox(
                                value: _selectedType == OddsType.probability,
                                onTap: () async {
                                  setState(() => _selectedType = OddsType.probability);
                                  final prefs = await SharedPreferences.getInstance();
                                  prefs.setString('odds_type', 'P');
                                  ref.read(oddsTypeProvider.notifier).state = 'P';
                                },
                              ),
                            ),
                          ),
                        ],
                      ),

                    ],
                  ),
                  const SizedBox(height: 29),
                  CustomDivider(),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                OddDescriptionText(
                  title: 'Decimal Odd',
                  subtitle:
                      'The number represents the multiplier on return from wagered amounts. Ex. 1.91, 1.83, 2.05, 7.5',
                ),
                const SizedBox(height: 24),
                OddDescriptionText(
                  title: 'American Odd',
                  subtitle:
                      'The American odds displays a “+” or “–“ in front of the number. “–“ signifies the favourite / “+” represents the underdog.',
                ),
                const SizedBox(height: 24),
                OddDescriptionText(
                  title: 'Fraction Odd',
                  subtitle:
                      'Literally as it sounds but counter intuitive, the denominator is essentially (x-1) in the sense a 33% would be 1/2 instead of 1/3. Ex. 1/1 (50% or +100 or 2.00), 1/2, 1/3, 4/1, 6/1, 9/1',
                ),
                OddDescriptionText(
                  title: 'Probability',
                  subtitle:
                      'Displays the probability of the outcome as a percentage. Ex. 50%, 33.33%, 66.67%, 85%',
                ),
              ],
            ),
          ],
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
