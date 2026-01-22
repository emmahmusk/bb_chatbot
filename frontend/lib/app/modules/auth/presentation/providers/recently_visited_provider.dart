import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../dashboard/data/models/visited_stock_model.dart';


final recentlyVisitedProvider =
    StateNotifierProvider<RecentlyVisitedNotifier, List<VisitedStockModel>>(
  (ref) => RecentlyVisitedNotifier(),
);

class RecentlyVisitedNotifier extends StateNotifier<List<VisitedStockModel>> {
  RecentlyVisitedNotifier() : super([]);

  void add(VisitedStockModel stock) {
    state = state.where((s) => s.id != stock.id).toList(); // Remove duplicates
    state = [stock, ...state]; // Add new on top
    if (state.length > 10) {
      state = state.sublist(0, 10); // Keep only latest 10
    }
  }
}
