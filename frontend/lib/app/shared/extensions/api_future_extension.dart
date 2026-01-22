import 'package:frontend/app/shared/extensions/dart_z_extension.dart';
import 'package:frontend/app/shared/functions/api_functions.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';

extension K<T> on ApiFuture<T> {
  Future<AppState<T>> get toState async {
    final r = (await this);
    if (r.isLeft()) {
      return SuccessState(r.left);
    }
    return ErrorState(r.right.message);
  }
}
