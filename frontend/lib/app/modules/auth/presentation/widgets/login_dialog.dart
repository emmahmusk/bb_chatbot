import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/modules/auth/domain/repositories/auth_repository.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/auth_dialog.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/create_account_dialog.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/forgot_password_dialog.dart';
import 'package:frontend/app/shared/classes/http/failures.dart';
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
  String? loginError;

  String _loginErrorMessage(Object? error) {
    final message = error is FailureResponse
        ? error.message.trim()
        : error?.toString().trim() ?? '';
    return message.isEmpty ? 'Unable to sign in. Please try again.' : message;
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    return AuthDialog(
      height: 680,
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
                loginError = null;
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
                loginError = null;
              });
            },
          ),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 180),
            child: loginError == null
                ? const SizedBox.shrink()
                : Container(
                    key: ValueKey(loginError),
                    width: double.infinity,
                    margin: const EdgeInsets.only(top: 14),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEF4444).withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: const Color(0xFFEF4444).withValues(alpha: 0.55),
                      ),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.error_outline_rounded,
                          color: Color(0xFFFCA5A5),
                          size: 18,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Semantics(
                            liveRegion: true,
                            child: Text(
                              loginError!,
                              style: const TextStyle(
                                color: Color(0xFFFCA5A5),
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                height: 1.35,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
          ),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.centerRight,
            child: Clickable(
              onClick: () {
                popAndShowCenterDialog(
                  context,
                  const ForgotPasswordDialog(),
                );
              },
              child: Text(
                'Forgot password?',
                style: TextStyle(
                  color: colors.alwaysWhite,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ),
          const SizedBox(height: 42),
          CustomButton(
            text: 'Next',
            onPressed: () async {
              if (loginError != null) {
                setState(() {
                  loginError = null;
                });
              }

              final repo = ref.read(authRepositoryProvider);
              
              // ✅ AWAIT the perform function to complete
              await perform(
                context,
                response: repo.login(username: username, password: password),
                showSuccess: false,
                onError: (error) {
                  if (!mounted) return;
                  setState(() {
                    loginError = _loginErrorMessage(error);
                  });
                },
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
