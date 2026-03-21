import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/classes/fonts/fonts.dart';
import 'package:frontend/app/shared/classes/http/http.dart';
import 'package:frontend/app/shared/classes/preferences/preferences.dart';
import 'package:frontend/app/shared/providers/preferences_provider.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/core/env/config.dart';
import 'package:frontend/core/navigation/router.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:shared_preferences/shared_preferences.dart';
// import 'package:shared_preferences/shared_preferences.dart';
// import 'package:frontend/app/modules/auth/data/login_response_model.dart';

// Future<Profile?> loadUserSession() async {
//   final prefs = await SharedPreferences.getInstance();
//   final user = prefs.getInt('user_id');
//   final id = prefs.getInt('profile_id');
//   final emailVerified = prefs.getBool('email_verified');

//   if (user != null && id != null && emailVerified != null) {
//     return Profile(id: id, user: user, emailVerified: emailVerified);
//   }
//   return null;
// }

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Preferences.initialize();
  const env = String.fromEnvironment("ENV", defaultValue: "dev");
  final config = await loadConfig(Environment.fromString(env));
  runApp(ProviderScope(child: MyApp(config: config)));

}


class MyApp extends ConsumerStatefulWidget {
  final Config config;

  const MyApp({
    super.key,
    required this.config,
  });

  @override
  ConsumerState<MyApp> createState() => _MyAppState();
}

class _MyAppState extends ConsumerState<MyApp> {
Future<void> _hydrateSession() async {
  final prefs = await SharedPreferences.getInstance();

   // ✅ Set default only if not already set
  final oddsType = prefs.getString('odds_type') ?? 'P';
  
  if (oddsType.isEmpty) {
    await prefs.setString('odds_type', 'P');
  }
  print("Selected Odds type is: $oddsType");
  
  final userId = prefs.getInt('user_id');
  final profileId = prefs.getInt('profile_id');
  final emailVerified = prefs.getBool('email_verified');

  final fullName = prefs.getString('full_name') ?? "N/A";
  final email = prefs.getString('email') ?? "N/A";
  final dateOfBirth = prefs.getString('date_of_birth') ?? "N/A";
  final phoneNumber = prefs.getString('phone_number') ?? "N/A";
  final physicalAddress = prefs.getString('physical_address') ?? "N/A";
   final walletBalance = prefs.getString('wallet_balance') ?? "N/A";
  final walletCoinBalance = prefs.getString('wallet_coin_balance') ?? "0.00";
  if (userId != null && profileId != null && emailVerified != null) {
    final profile = Profile(
      id: profileId,
      user: userId,
      emailVerified: emailVerified,
      fullName: fullName,
      email: email,
      dateOfBirth: dateOfBirth,
      phoneNumber: phoneNumber,
      physicalAddress: physicalAddress,
      walletBalance: walletBalance,
      walletCoinBalance: walletCoinBalance,
    );

    ref.read(currentUserProvider.notifier).state = profile;
  }
  // Initialize global odds preference provider from SharedPreferences
  ref.read(oddsTypeProvider.notifier).state = oddsType;
}




  @override
  void initState() {
    onInit(
      () {
        final http = ref.read(httpProvider);
        http.setBaseUrl(widget.config.baseUrl);

        // ✅ Log base URL once
        print("🌍 Base URL set to: ${http.baseUrl}");
        _hydrateSession(); 
      },
    );
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Bullbear',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
        fontFamily: Fonts.poppins,
      ),
      routerConfig: router,
    );
  }
}
