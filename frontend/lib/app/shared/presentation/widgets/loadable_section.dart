import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/shared/presentation/widgets/error_main_card.dart';
import 'package:frontend/app/shared/presentation/widgets/loading_main_card.dart';
import 'package:frontend/core/framework/mgt/app_state.dart';

class LoadableSection<T> extends ConsumerWidget {
  final AppState<T> state;
  final Widget Function(BuildContext context, T data) builder;
  final double sizeFactor;
  const LoadableSection({
    super.key,
    required this.state,
    required this.builder,
    this.sizeFactor = 1,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (state.isInitial) {
      return const SizedBox();
    }
    if (state.isLoading) {
      return LoadingMainCard();
    }
    if (state.isError) {
      return ErrorMainCard(
        message: state.errorMessage,
      );
    }
    return builder(context, state.data);
  }
}
