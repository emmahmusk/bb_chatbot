import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/dto/signup_dto.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/modules/auth/domain/endpoints/auth_endpoints.dart';
import 'package:frontend/app/shared/classes/http/http.dart';
import 'package:frontend/app/shared/classes/preferences/preferences.dart';
import 'package:frontend/app/shared/classes/preferences/preferences_strings.dart';
import 'package:frontend/app/shared/functions/api_functions.dart';

final authRepositoryProvider = Provider((ref) {
  final http = ref.read(httpProvider);
  return AuthRepository(http: http);
});

class AuthRepository {
  final HTTP http;

  AuthRepository({required this.http});

  ApiFuture<LoginResponseModel> login({
    required String username,
    required String password,
  }) {
    return postCall(
      http,
      endpoint: AuthEndpoints.login,
      onResponseBody: (r, _) {
        print("Login Response Chethan: ");
        print(r);
        final model = LoginResponseModel.fromJson(r);
        http.addHeader(
          key: "Authorization",
          value: "Token ${model.access}",
        );
        Preferences.setModel(
          key: PreferencesStrings.loginResponseModel,
          model: model,
        );
        return model;
      },
      body: {
        "username": username,
        "password": password,
      },
    );
  }

  ApiFuture<void> signup({required SignupDto dto}) {
    return postCall(
      http,
      acceptableStatusCodes: [200, 201],
      endpoint: AuthEndpoints.signup,
      onResponseBody: (r, _) {},
      body: dto.toJson(),
    );
  }

  ApiFuture<String> requestPasswordReset({
    required String email,
  }) {
    return postCall(
      http,
      endpoint: AuthEndpoints.passwordResetRequest,
      acceptableStatusCodes: const [200],
      onResponseBody: (r, _) => (r['message'] ?? 'OTP sent').toString(),
      body: {
        "email": email,
      },
    );
  }

  ApiFuture<String> verifyPasswordReset({
    required String email,
    required String otpCode,
    required String newPassword,
  }) {
    return postCall(
      http,
      endpoint: AuthEndpoints.passwordResetVerify,
      acceptableStatusCodes: const [200],
      onResponseBody: (r, _) => (r['message'] ?? 'Password reset successful').toString(),
      body: {
        "email": email,
        "otp_code": otpCode,
        "new_password": newPassword,
      },
    );
  }
}
