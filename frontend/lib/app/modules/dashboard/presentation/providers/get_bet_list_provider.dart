import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/dashboard/data/models/markets_model.dart';

final betListProvider = StateProvider<List<MarketModel>>(
  (_) => [],
);
