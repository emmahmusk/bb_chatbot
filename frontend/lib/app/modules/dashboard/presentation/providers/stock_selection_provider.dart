import 'package:flutter_riverpod/flutter_riverpod.dart';
 
import '../../data/models/user_stock_selection_model.dart';
class SelectedStockNotifier extends StateNotifier<List<SelectedStockModel>> {
  SelectedStockNotifier() : super([]);

  void insertOrUpdate(SelectedStockModel stock) {
    final index = state.indexWhere((s) => s.marketId == stock.marketId);
    if (index != -1) {
      // Update
      state = [
        ...state.sublist(0, index),
        stock,
        ...state.sublist(index + 1),
      ];
    } else {
      // Insert
      state = [...state, stock];
    }
  }

  void remove(int marketId) {
    state = state.where((s) => s.marketId != marketId).toList();
  }

  void clear() {
    state = [];
  }
}

final selectedStockProvider =
    StateNotifierProvider<SelectedStockNotifier, List<SelectedStockModel>>(
  (ref) => SelectedStockNotifier(),
);
