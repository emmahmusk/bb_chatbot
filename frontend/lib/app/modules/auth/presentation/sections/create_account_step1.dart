import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/providers/signup_dto_notifier.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/login_dialog.dart';
import 'package:frontend/app/shared/extensions/string_extension.dart';
import 'package:frontend/app/shared/presentation/widgets/clickable.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_button.dart';
import 'package:frontend/app/shared/presentation/widgets/custom_textfield.dart';
import 'package:frontend/app/shared/presentation/widgets/title_subtitle.dart';
import 'package:frontend/core/framework/theme/colors/app_theme_provider.dart';
import 'package:frontend/core/navigation/navigator.dart';

class CreateAccountStep1 extends ConsumerStatefulWidget {
  const CreateAccountStep1({
    super.key,
    required this.onNext,
  });
  final Function()? onNext;

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _CreateAccountStep1State();
}

class _CreateAccountStep1State extends ConsumerState<CreateAccountStep1> {
  // local state for each segment
  String _dobYear = '';
  String _dobMonth = '';
  String _dobDay = '';

  void _updateDob(SignupDtoNotifier notifier) {
    // only set when all three segments are non‐empty
    if (_dobYear.length == 4 && _dobMonth.isNotEmpty && _dobDay.isNotEmpty) {
      final paddedMonth = _dobMonth.padLeft(2, '0');
      final paddedDay = _dobDay.padLeft(2, '0');
      notifier.setDateOfBirth('$_dobYear-$paddedMonth-$paddedDay');
    }
  }

  @override
  Widget build(BuildContext context) {
    final dto = ref.watch(signupDtoProvider);
    final notifier = ref.read(signupDtoProvider.notifier);
    final colors = ref.watch(appThemeProvider).colors;

    return SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.max,
        children: [
          Center(
            child: TitleSubtitle(
                title: 'Create Account',
                subtitle:
                  'Enter your personal details to create your account.',
            ),
          ),
          const SizedBox(height: 44),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Expanded(
                child: CustomTextField(
                  headerText: 'First name (as shown on ID)',
                  hint: 'Jane',
                  onChanged: notifier.setFirstName,
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: CustomTextField(
                  headerText: 'Last name (as shown on ID)',
                  hint: 'Doe',
                  onChanged: notifier.setLastName,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              
              Expanded(
                child: CustomTextField(
                  headerText: 'Date of Birth',
                  hint: 'MM',
                  keyboardType: TextInputType.number,
                  onChanged: (m) {
                    _dobMonth = m;
                    _updateDob(notifier);
                  },
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly,
                    LengthLimitingTextInputFormatter(2),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: CustomTextField(
                  headerText: '',
                  hint: 'DD',
                  keyboardType: TextInputType.number,
                  onChanged: (d) {
                    _dobDay = d;
                    _updateDob(notifier);
                  },
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly,
                    LengthLimitingTextInputFormatter(2),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: CustomTextField(
                  headerText: '',
                  hint: 'YYYY',
                  keyboardType: TextInputType.number,
                  onChanged: (y) {
                    _dobYear = y;
                    _updateDob(notifier);
                  },
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly,
                    LengthLimitingTextInputFormatter(4),
                  ],
                ),
              ),
              
              
            ],
          ),
          const SizedBox(height: 24),
          CustomTextField(
            headerText: 'Username',
            hint: 'Enter your username',
            onChanged: notifier.setUsername,
          ),
          const SizedBox(height: 24),
          CustomTextField(
            headerText: 'Password',
            hint: 'Enter your password',
            isPassword: true,
            onChanged: notifier.setPassword,
          ),
          const SizedBox(height: 44),
          CustomButton(
            text: 'Next',
            onPressed: widget.onNext,
            validator: () {
              return dto.firstName.isNotEmpty &&
                  dto.lastName.isNotEmpty &&
                  dto.dateOfBirth.isNotEmpty &&
                  dto.username.isNotEmpty &&
                  (dto.password.isNotEmptyAndLongerThan5);
            },
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Already have an account? ',
                style: TextStyle(
                  color: colors.always8B949E,
                  fontSize: 14,
                  fontWeight: FontWeight.w400,
                ),
              ),
              Clickable(
                onClick: () {
                  popAndShowCenterDialog(context, LoginDialog());
                },
                child: Text(
                  'Log in',
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
