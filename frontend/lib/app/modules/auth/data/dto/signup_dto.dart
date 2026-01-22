class SignupDto {
  final String username;
  final String email;
  final String password;
  final String firstName;
  final String lastName;
  final String dateOfBirth;
  final String currentAddress;
  final String city;
  final String postalCode;
  final String phone;

  SignupDto({
    required this.username,
    required this.email,
    required this.password,
    required this.firstName,
    required this.lastName,
    required this.dateOfBirth,
    required this.currentAddress,
    required this.city,
    required this.postalCode,
    required this.phone,
  });

  SignupDto copyWith({
    String? username,
    String? email,
    String? password,
    String? firstName,
    String? lastName,
    String? dateOfBirth,
    String? currentAddress,
    String? city,
    String? postalCode,
    String? phone,
  }) {
    return SignupDto(
      username: username ?? this.username,
      email: email ?? this.email,
      password: password ?? this.password,
      firstName: firstName ?? this.firstName,
      lastName: lastName ?? this.lastName,
      dateOfBirth: dateOfBirth ?? this.dateOfBirth,
      currentAddress: currentAddress ?? this.currentAddress,
      city: city ?? this.city,
      postalCode: postalCode ?? this.postalCode,
      phone: phone ?? this.phone,
    );
  }

  factory SignupDto.empty() => SignupDto(
        username: '',
        email: '',
        password: '',
        firstName: '',
        lastName: '',
        dateOfBirth: '',
        currentAddress: '',
        city: '',
        postalCode: '',
        phone: '',
      );

  Map<String, dynamic> toJson() => {
        'username': username,
        'email': email,
        'password': password,
        'first_name': firstName,
        'last_name': lastName,
        'date_of_birth': dateOfBirth,
        'current_address': currentAddress,
        'city': city,
        'postal_code': postalCode,
        'phone': phone,
      };
}
