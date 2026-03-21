import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/classes/preferences/preferences.dart';

final currentUserProvider = StateProvider<Profile?>((_) => null);

class LoginResponseModel extends Cachable {
  final Profile profile;
  final String access;
  final String refresh;

  LoginResponseModel({
    required this.profile,
    required this.access,
    required this.refresh,
  });

  factory LoginResponseModel.fromJson(Map<String, dynamic> json) {
    return LoginResponseModel(
      profile: Profile.fromJson(json['profile'] as Map<String, dynamic>),
      access: json['access'] as String,
      refresh: json['refresh'] as String,
    );
  }

  @override
  Map<String, dynamic> toMap() => {
        'profile': profile.toMap(),
        'access': access,
        'refresh': refresh,
      };
}

class Profile extends Cachable {
  final int id;
  final int user;
  final bool emailVerified;
  final String fullName;
  final String email;
  final String dateOfBirth;
  final String phoneNumber;
  final String physicalAddress;
  final String walletBalance;
  final String walletCoinBalance;

  Profile({
    required this.id,
    required this.user,
    required this.emailVerified,
    required this.fullName,
    required this.email,
    required this.dateOfBirth,
    required this.phoneNumber,
    required this.physicalAddress,
    required this.walletBalance,
    required this.walletCoinBalance,
  });

  factory Profile.fromJson(Map<String, dynamic> json) {
    return Profile(
      id: json['id'] as int,
      user: json['user'] as int,
      emailVerified: json['email_verified'] as bool,
      fullName: json['full_name'] ?? "N/A",
      email: json['email'] ?? "N/A",
      dateOfBirth: json['date_of_birth'] ?? "N/A",
      phoneNumber: json['phone_number'] ?? "N/A",
      physicalAddress: json['physical_address'] ?? "N/A",
      walletBalance: json['wallet_balance'] ?? "N/A",
      walletCoinBalance: json['wallet_coin_balance'] ?? "0.00",
    );
  }

  @override
  Map<String, dynamic> toMap() => {
        'id': id,
        'user': user,
        'email_verified': emailVerified,
        'full_name': fullName,
        'email': email,
        'date_of_birth': dateOfBirth,
        'phone_number': phoneNumber,
        'physical_address': physicalAddress,
        'wallet_balance': walletBalance,
        'wallet_coin_balance': walletCoinBalance,
      };
}

