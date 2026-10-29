import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

enum Environment {
  dev,
  prod,
  stg;

 static Environment fromString(String value) {
    switch (value) {
      case 'dev':
        return Environment.dev;
      case 'prod':
        return Environment.prod;
      case 'stg':
        return Environment.stg;
      default:
        throw Exception('Unknown environment');
    }
  }
}

class Config {
  final String baseUrl;
  final String chatbotBaseUrl;
  final String sportsbookMode;
  final Environment environment;

  Config({
    required this.baseUrl,
    this.chatbotBaseUrl = '',
    this.sportsbookMode = 'live',
    required this.environment,
  });
}

Future<Config> loadConfig(Environment env) async {
  final configString = await rootBundle.loadString(
    'config/config_${env.name}.json',
  );
  final Map<String, dynamic> configJson = json.decode(configString);
  return Config(
    baseUrl: configJson['baseUrl'],
    chatbotBaseUrl: (configJson['chatbotBaseUrl'] ?? '').toString(),
    sportsbookMode: const String.fromEnvironment('SPORTSBOOK_MODE', defaultValue: 'live'),
    environment: env,
  );
}
