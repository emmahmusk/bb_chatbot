import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/domain/repositories/auth_repository.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/auth_dialog.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/shared/extensions/context_extension.dart';
import 'package:frontend/app/shared/functions/app_functions.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_textfield.dart';
import 'package:frontend/app/shared/presentation\widgets/title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';

enum _ResetStep {
  request,
  verify,
}

class ForgotPasswordDialog extends ConsumerStatefulWidget {
  const ForgotPasswordDialog({super.key});

  @override
  ConsumerState<ForgotPasswordDialog> createState() => _ForgotPasswordDialogState();
}

class _ForgotPasswordDialogState extends ConsumerState<ForgotPasswordDialog> {
  final _emailController = TextEditingController();
  final _otpController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  _ResetStep _step = _ResetStep.request;

  @override
  void dispose() {
    _emailController.dispose();
    _otpController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  String get _email => _emailController.text.trim();
  String get _otp => _otpController.text.trim();
  String get _newPassword => _newPasswordController.text.trim();
  String get _confirmPassword => _confirmPasswordController.text.trim();

  Future<void> _requestOtp() async {
    final repo = ref.read(authRepositoryProvider);

    await perform<String>(
      context,
      response: repo.requestPasswordReset(email: _email),
      showSuccess: false,
      onSuccess: (message) {
        if (!mounted) return;
        setState(() {
          _step = _ResetStep.verify;
        });
        context.showSuccess(message);
      },
    );
  }

  Future<void> _resetPassword() async {
    final repo = ref.read(authRepositoryProvider);

    await perform<String>(
      context,
      response: repo.verifyPasswordReset(
        email: _email,
        otpCode: _otp,
        newPassword: _newPassword,
      ),
      showSuccess: false,
      onSuccess: (message) {
        if (!mounted) return;
        context.showSuccess(message);
        popAndShowCenterDialog(context, const LoginDialog());
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final isRequestStep = _step == _ResetStep.request;

    return AuthDialog(
      height: isRequestStep ? 470 : 620,
      child: Column(
        children: [
          Center(
            child: TitleSubtitle(
              title: isRequestStep ? 'Forgot Password' : 'Reset Password',
              subtitle: isRequestStep
                  ? 'Enter your email to receive a reset code.'
                  : 'Enter the code sent to your email and choose a new password.',
            ),
          ),
          const SizedBox(height: 32),
          CustomTextField(
            headerText: 'Email',
            hint: 'Enter your email',
            keyboardType: TextInputType.emailAddress,
            textEditingController: _emailController,
            onChanged: (_) => setState(() {}),
          ),
          if (!isRequestStep) ...[
            const SizedBox(height: 20),
            CustomTextField(
              headerText: 'OTP Code',
              hint: 'Enter the 6-digit code',
              keyboardType: TextInputType.number,
              maxLength: 6,
              textEditingController: _otpController,
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 20),
            CustomTextField(
              headerText: 'New Password',
              hint: 'Enter your new password',
              isPassword: true,
              textEditingController: _newPasswordController,
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 20),
            CustomTextField(
              headerText: 'Confirm Password',
              hint: 'Re-enter your new password',
              isPassword: true,
              textEditingController: _confirmPasswordController,
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Clickable(
                  onClick: _email.isEmpty ? null : _requestOtp,
                  child: Text(
                    'Resend code',
                    style: TextStyle(
                      color: _email.isEmpty ? colors.always8B949E : colors.alwaysWhite,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 28),
          CustomButton(
            text: isRequestStep ? 'Send code' : 'Reset password',
            onPressed: isRequestStep ? _requestOtp : _resetPassword,
            validator: () {
              if (_email.isEmpty) return false;
              if (isRequestStep) return true;
              if (_otp.length != 6) return false;
              if (_newPassword.length < 8) return false;
              if (_confirmPassword != _newPassword) return false;
              return true;
            },
          ),
          if (!isRequestStep && _confirmPassword.isNotEmpty && _confirmPassword != _newPassword) ...[
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Passwords do not match.',
                style: TextStyle(
                  color: colors.error,
                  fontSize: 12,
                ),
              ),
            ),
          ],
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Clickable(
                onClick: () {
                  popAndShowCenterDialog(context, const LoginDialog());
                },
                child: Text(
                  'Back to login',
                  style: TextStyle(
                    color: colors.alwaysWhite,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
