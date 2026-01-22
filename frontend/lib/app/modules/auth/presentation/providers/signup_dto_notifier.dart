import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/dto/signup_dto.dart';

final signupDtoProvider = StateNotifierProvider<SignupDtoNotifier, SignupDto>(
  (ref) => SignupDtoNotifier(),
);

class SignupDtoNotifier extends StateNotifier<SignupDto> {
  SignupDtoNotifier() : super(SignupDto.empty());

  void setUsername(String u) => state = state.copyWith(username: u);
  void setEmail(String e) => state = state.copyWith(email: e);
  void setPassword(String p) => state = state.copyWith(password: p);
  void setFirstName(String n) => state = state.copyWith(firstName: n);
  void setLastName(String n) => state = state.copyWith(lastName: n);
  void setDateOfBirth(String d) => state = state.copyWith(dateOfBirth: d);
  void setCurrentAddress(String a) => state = state.copyWith(currentAddress: a);
  void setCity(String c) => state = state.copyWith(city: c);
  void setPostalCode(String c) => state = state.copyWith(postalCode: c);
  void setPhone(String p) => state = state.copyWith(phone: p);
}
