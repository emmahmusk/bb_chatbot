import 'package:equatable/equatable.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

typedef AppNotifier<T> = Notifier<AppState<T>>;

typedef AppNotifierProvider<K extends AppNotifier<T>, T>
    = NotifierProvider<K, AppState<T>>;

StateProvider<T> setProvider<T>(T v) => StateProvider((_) => v);

sealed class AppState<T> extends Equatable {
  const AppState();
  @override
  List<Object?> get props => [];

  bool get isLoading => this is LoadingState<T>;
  bool get isSuccess => this is SuccessState<T>;
  bool get isError => this is ErrorState<T>;
  bool get isLoadMore => this is LoadMoreState<T>;
  bool get isErrorData => this is ErrorDataState<T>;
  bool get isInitial => this is Init<T>;

  LoadingState<T> get asLoading => this as LoadingState<T>;
  SuccessState<T> get asSuccess => this as SuccessState<T>;
  ErrorState<T> get asError => this as ErrorState<T>;
  LoadMoreState<T> get asLoadMore => this as LoadMoreState<T>;
  ErrorDataState<T> get asErrorData => this as ErrorDataState<T>;

  String get errorMessage {
    if (isError) {
      return asError.message;
    }
    if (isErrorData) {
      return asErrorData.message;
    }
    return "";
  }

  T get data {
    if (isSuccess) {
      return asSuccess.data;
    }
    if (isLoadMore) {
      return asLoadMore.data;
    }
    return asErrorData.data;
  }

  T dataOrElse(T defaultValue) {
    if (isSuccess) {
      return asSuccess.data;
    }
    if (isLoadMore) {
      return asLoadMore.data;
    }
    if (isErrorData) {
      return asErrorData.data;
    }
    return defaultValue;
  }

  factory AppState.initial() => Init<T>();
  factory AppState.loading() => LoadingState<T>();
  factory AppState.success(T data, {String? message}) =>
      SuccessState<T>(data, message: message);
  factory AppState.error(String message) => ErrorState<T>(message);
  factory AppState.loadingMore(T data, {String? message}) =>
      LoadMoreState<T>(data, message: message);
}

class Init<T> extends AppState<T> {
  const Init();
}

class LoadingState<T> extends AppState<T> {
  const LoadingState();

  @override
  List<Object?> get props => [];
}

class LoadMoreState<T> extends AppState<T> {
  @override
  final T data;
  final String? message;
  const LoadMoreState(
    this.data, {
    this.message,
  });

  @override
  List<Object?> get props => [data, message];
}

class ErrorDataState<T> extends AppState<T> {
  @override
  final T data;
  final String message;
  const ErrorDataState({
    required this.data,
    required this.message,
  });

  @override
  List<Object?> get props => [data, message];
}

class ErrorState<T> extends AppState<T> {
  final String message;
  const ErrorState(this.message);

  @override
  List<Object?> get props => [message];
}

class SuccessState<T> extends AppState<T> {
  @override
  final T data;
  final String? message;
  const SuccessState(
    this.data, {
    this.message,
  });

  @override
  List<Object?> get props => [data, message];
}
