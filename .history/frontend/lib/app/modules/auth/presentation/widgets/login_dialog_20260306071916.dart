import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/modules/auth/domain/repositories/auth_repository.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/auth_dialog.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/create_account_dialog.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_textfield.dart';
import 'package:frontend/app/shared/presentation/widgets/title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';
 import 'package:shared_preferences/shared_preferences.dart';

class LoginDialog extends ConsumerStatefulWidget {
  const LoginDialog({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _LoginDialogState();
}

class _LoginDialogState extends ConsumerState<LoginDialog> {
  String username = "";
  String password = "";

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    return AuthDialog(
      child: Column(
        children: [
          Center(
            child: TitleSubtitle(
                title: 'Welcome Back',
                subtitle: 'Sign in to your account.',
            ),
          ),
          const SizedBox(height: 42),
          CustomTextField(
            headerText: 'Username',
            hint: 'Enter your username',
            onChanged: (value) {
              setState(() {
                username = value;
              });
            },
          ),
          const SizedBox(height: 23),
          CustomTextField(
            headerText: 'Password',
            hint: 'Enter your password',
            isPassword: true,
            onChanged: (pass) {
              setState(() {
                password = pass;
              });
            },
          ),
          const SizedBox(height: 42),
          CustomButton(
            text: 'Next',
            onPressed: () async {
              final repo = ref.read(authRepositoryProvider);
              
              // ✅ AWAIT the perform function to complete
              await perform(
                context,
                response: repo.login(username: username, password: password),
                onSuccess: (d) async {
                  ref.read(currentUserProvider.notifier).state = d.profile;
                  
                  // Save in SharedPreferences
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setInt('user_id', d.profile.user);
                  await prefs.setBool('email_verified', d.profile.emailVerified);
                  await prefs.setInt('profile_id', d.profile.id);
                  await prefs.setString('access_token', d.access);
                  await prefs.setString('wallet_balance', d.profile.walletBalance);
                    await prefs.setString('wallet_coin_balance', d.profile.walletCoinBalance);
                  print("Login Token: ${d.access}");
                  await prefs.setString('refresh_token', d.refresh);

                  // 🔽 Save additional profile fields
                  await prefs.setString('full_name', d.profile.fullName);
                  await prefs.setString('email', d.profile.email);
                  await prefs.setString('date_of_birth', d.profile.dateOfBirth);
                  await prefs.setString('phone_number', d.profile.phoneNumber);
                  await prefs.setString('physical_address', d.profile.physicalAddress);
                  
                  // ✅ Pop login dialog after everything is saved
                  if (context.mounted) pop(context);
                },
              );
            },
            validator: () {
              return username.isNotEmpty && password.isNotEmpty;
            },
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Don\'t have an account? ',
                style: TextStyle(
                  color: colors.always8B949E,
                  fontSize: 14,
                  fontWeight: FontWeight.w400,
                ),
              ),
              Clickable(
                onClick: () {
                  popAndShowCenterDialog(
                    context,
                    CreateAccountDialog(),
                  );
                },
                child: Text(
                  'Register here',
                  style: TextStyle(
                    color: colors.alwaysWhite,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(width: 4),
              Icon(
                Icons.arrow_forward_ios,
                size: 8,
                color: colors.alwaysWhite,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
