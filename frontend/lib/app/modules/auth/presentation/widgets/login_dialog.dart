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
              subtitle:
                  'Lorem ipsum dolor sit amet, consectetur adipiscing elit',
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
            onPressed: () {
              final repo = ref.read(authRepositoryProvider);
              perform(
                context,
                response: repo.login(username: username, password: password),
                onSuccess: (d)async {
                   
                  ref.read(currentUserProvider.notifier).state = d.profile;
                  // popAndShowCenterDialog(
                  //   context,
                  //   VerifyAccountDialog(),
                  // );
                  // Save in SharedPreferences
                    final prefs = await SharedPreferences.getInstance();
                    prefs.setInt('user_id', d.profile.user);
                    prefs.setBool('email_verified', d.profile.emailVerified);
                    prefs.setInt('profile_id', d.profile.id);
                    prefs.setString('access_token', d.access);
                    prefs.setString('wallet_balance',d.profile.walletBalance);
                    print("Chethan TOken");
                    print(d.access);
                    prefs.setString('refresh_token', d.refresh);

                    // 🔽 Save additional profile fields
                    prefs.setString('full_name', d.profile.fullName);
                    prefs.setString('email', d.profile.email);
                    prefs.setString('date_of_birth', d.profile.dateOfBirth);
                    prefs.setString('phone_number', d.profile.phoneNumber);
                    prefs.setString('physical_address', d.profile.physicalAddress);
                  pop(context);
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
