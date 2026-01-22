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
  final Environment environment;

  Config({
    required this.baseUrl,
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
    environment: env,
  );
}
