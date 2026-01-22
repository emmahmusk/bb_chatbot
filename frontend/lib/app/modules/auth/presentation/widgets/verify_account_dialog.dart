import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/auth_dialog.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:pin_code_fields/pin_code_fields.dart';

class VerifyAccountDialog extends ConsumerStatefulWidget {
  final void Function(String code)? onSubmit;
  final VoidCallback? onResend;

  const VerifyAccountDialog({
    super.key,
    this.onSubmit,
    this.onResend,
  });

  @override
  ConsumerState<VerifyAccountDialog> createState() =>
      _VerifyAccountDialogState();
}

class _VerifyAccountDialogState extends ConsumerState<VerifyAccountDialog> {
  static const int _otpLength = 6;

  String _currentCode = '';
  bool _hasError = false;

  Timer? _timer;
  int _secondsRemaining = 60;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  void _startTimer() {
    _timer?.cancel();
    setState(() => _secondsRemaining = 60);

    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (mounted) {
        if (_secondsRemaining > 0) {
          setState(() => _secondsRemaining--);
        } else {
          t.cancel();
        }
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = ref.watch(appThemeProvider).colors;
    final isComplete = _currentCode.length == _otpLength;

    final textStyle = TextStyle(
      fontSize: 14,
      color: colors.alwaysWhite,
    );

    return AuthDialog(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: TitleSubtitle(
              title: 'Verify Account',
              subtitle:
                  'Lorem ipsum dolor sit amet, consectetur adipiscing elit',
            ),
          ),
          const SizedBox(height: 42),
          Text(
            'OTP Code',
            style: textStyle,
          ),
          const SizedBox(height: 6),
          PinCodeTextField(
            length: _otpLength,
            appContext: context,
            obscureText: false,
            blinkDuration: const Duration(milliseconds: 300),
            animationType: AnimationType.fade,
            textStyle: textStyle,
            pastedTextStyle: textStyle,
            cursorColor: colors.alwaysWhite,
            cursorHeight: 20,
            cursorWidth: 1,
            useHapticFeedback: true,
            pinTheme: PinTheme(
              shape: PinCodeFieldShape.box,
              borderRadius: BorderRadius.circular(12),
              fieldHeight: 48,
              fieldWidth: 64,
              borderWidth: 1,
              activeBorderWidth: 1,
              selectedBorderWidth: 1,
              inactiveBorderWidth: 1,
              errorBorderWidth: 1,
              activeColor: _hasError ? colors.error : colors.primary,
              selectedColor: colors.primary,
              inactiveColor: _hasError ? colors.error : colors.always30363D,
              activeFillColor: colors.always1F242C,
              selectedFillColor: colors.always1F242C,
              inactiveFillColor: colors.always1F242C,
            ),
            enableActiveFill: true,
            onChanged: (value) {
              if (_hasError) setState(() => _hasError = false);
              setState(() => _currentCode = value);
            },
            onCompleted: (value) {
              setState(() => _currentCode = value);
            },
          ),
          const SizedBox(height: 8),
          if (_secondsRemaining > 0)
            Text(
              'Resend code in 0:${_secondsRemaining.toString().padLeft(2, '0')} secs',
              style: TextStyle(color: colors.alwaysWhite, fontSize: 12),
            )
          else
            Clickable(
              onClick: () {
                widget.onResend?.call();
                _startTimer();
                setState(() {
                  _currentCode = '';
                  _hasError = false;
                });
              },
              child: Text(
                'Resend code',
                style: TextStyle(color: colors.alwaysWhite, fontSize: 12),
              ),
            ),
          const SizedBox(height: 100),
          CustomButton(
            text: 'Verify account',
            onPressed: () {},
            validator: () => isComplete,
          ),
        ],
      ),
    );
  }
}
