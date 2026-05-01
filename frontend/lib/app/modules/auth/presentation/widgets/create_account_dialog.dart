import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/presentation/sections/create_account_step1.dart';
import 'package:frontend/app/modules/auth/presentation/sections/create_account_step2.dart';
import 'package:frontend/app/modules/auth/presentation/widgets/auth_dialog.dart';

class CreateAccountDialog extends ConsumerStatefulWidget {
  const CreateAccountDialog({super.key});

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _CreateAccountDialogState();
}

class _CreateAccountDialogState extends ConsumerState<CreateAccountDialog> {
  int currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    return AuthDialog(
      // height: MediaQuery.of(context).size.height * 10.0,
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 300),
        switchInCurve: Curves.easeOut,
        switchOutCurve: Curves.easeIn,
        transitionBuilder: (Widget child, Animation<double> animation) {
          return FadeTransition(
            opacity: animation,
            child: child,
          );
        },
        child: _buildStep(key: ValueKey(currentIndex)),
      ),
    );
  }

  Widget _buildStep({required Key key}) {
    switch (currentIndex) {
      case 0:
        return CreateAccountStep1(
          key: key,
          onNext: () => setState(() => currentIndex = 1),
        );
      case 1:
        return CreateAccountStep2(
          key: key,
          onBack: () => setState(() => currentIndex = 0),
        );
      default:
        throw UnimplementedError();
    }
  }
}
