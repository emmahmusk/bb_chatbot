import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/shared/classes/preferences/preferences.dart';
import 'package:frontend/app/shared/classes/preferences/preferences_strings.dart';
import 'package:frontend/app/shared/extensions/context_extension.dart';
import 'package:frontend/app/shared/extensions/dart_z_extension.dart';
import 'package:frontend/app/shared/functions/api_functions.dart';
import 'package:frontend/app/shared/functions/dialog_functions.dart';
import 'package:frontend/core/navigation/navigator.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

void onInit(VoidCallback callback) {
  SchedulerBinding.instance.addPostFrameCallback((_) {
    callback();
  });
}

Future<void> perform<T>(
  BuildContext context, {
  required ApiFuture<T> response,
  required Function(T) onSuccess,
  Function(dynamic)? onError,
  bool popAfterSuccess = false,
  bool showSuccess = true,
  String successMessage = "Successful",
}) async {
  showLoadingDialog(context);
  response.then(
    (x) {
      pop(context);

      if (x.isRight()) {
        onError?.call(x.right) ?? context.showError(x.right.message);
        return;
      }
      if (popAfterSuccess) {
        pop(context);
      }
      if (showSuccess) {
        context.showSuccess(successMessage);
      }
      return onSuccess(x.left);
    },
  );
}

LoginResponseModel? getUser() {
  return Preferences.getModel<LoginResponseModel>(
    key: PreferencesStrings.loginResponseModel,
    creator: (json) => LoginResponseModel.fromJson(json),
  );
}

bool isAuthenticated() {
  return getUser() != null;
}

void logout(BuildContext context, WidgetRef ref) async{
  showLoadingDialog(context);
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString('odds_type', 'D');
  WidgetsBinding.instance.addPostFrameCallback((_) {
    Future.delayed(const Duration(seconds: 3), () {
      pop(context); // pop logout dialog
      pop(context); // pop loading dialog
      context.go('/dashboard/trending');
      Preferences.clear();
      // ✅ Reset odds_type to "D"
      

      ref.read(currentUserProvider.notifier).state = null;
    });
  });
}

void removeHashFromURL() {
  // setUrlStrategy(PathUrlStrategy());
}
