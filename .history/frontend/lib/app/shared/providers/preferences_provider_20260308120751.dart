import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Global provider for odds type preference stored as single-letter codes: 'D','A','F','P'
final oddsTypeProvider = StateProvider<String>((ref) => 'P');
