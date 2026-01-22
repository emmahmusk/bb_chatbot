import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dartz/dartz.dart';
import 'package:frontend/app/shared/classes/http/failures.dart';
import 'package:frontend/app/shared/classes/http/http.dart';
import 'package:frontend/app/shared/extensions/http_response_extension.dart';
import 'package:http/http.dart';

enum CallType { post, get, put, patch, delete, postWithFiles, postWithBytes }

typedef ApiFuture<T> = Future<Either<T, FailureResponse>>;

ApiFuture<T> postCall<T>(
  HTTP http, {
  String? overrideBaseUrl,
  required String endpoint,
  required FutureOr<T> Function(dynamic body, int code) onResponseBody,
  required Map<String, dynamic> body,
  List<int> acceptableStatusCodes = const [200],
  String? Function(Response response)? onOtherStatus,
  Function(Object e)? onException,
  bool isDebug = false,
  bool nonJsonResponse = false,
}) {
  return apiCall(
    http,
    overrideBaseUrl: overrideBaseUrl,
    endpoint: endpoint,
    type: CallType.post,
    onResponseBody: onResponseBody,
    acceptableStatusCodes: acceptableStatusCodes,
    body: body,
    onOtherStatus: onOtherStatus,
    onException: onException,
    isDebug: isDebug,
    nonJsonResponse: nonJsonResponse,
  );
}

ApiFuture<T> postWithFilesCall<T>(
  HTTP http, {
  required String endpoint,
  required FutureOr<T> Function(dynamic body, int code) onResponseBody,
  required List<({String key, File file})> files,
  required Map<String, String> body,
  List<int> acceptableStatusCodes = const [200],
  String? Function(Response response)? onOtherStatus,
  Function(Object e)? onException,
  bool isDebug = false,
  bool nonJsonResponse = false,
}) {
  return apiCall(
    http,
    endpoint: endpoint,
    type: CallType.postWithFiles,
    onResponseBody: onResponseBody,
    acceptableStatusCodes: acceptableStatusCodes,
    body: body,
    onOtherStatus: onOtherStatus,
    files: files,
    onException: onException,
    isDebug: isDebug,
    nonJsonResponse: nonJsonResponse,
  );
}

ApiFuture<T> postWithBytes<T>(
  HTTP http, {
  String? overrideBaseUrl,
  required String endpoint,
  required FutureOr<T> Function(dynamic body, int code) onResponseBody,
  required List<({String key, Uint8List byte, String extension})> bytes,
  required Map<String, String> body,
  List<int> acceptableStatusCodes = const [200],
  String? Function(Response response)? onOtherStatus,
  Function(Object e)? onException,
  bool isDebug = false,
  bool nonJsonResponse = false,
}) {
  return apiCall(
    http,
    overrideBaseUrl: overrideBaseUrl,
    endpoint: endpoint,
    type: CallType.postWithBytes,
    onResponseBody: onResponseBody,
    acceptableStatusCodes: acceptableStatusCodes,
    body: body,
    bytes: bytes,
    onOtherStatus: onOtherStatus,
    onException: onException,
    isDebug: isDebug,
    nonJsonResponse: nonJsonResponse,
  );
}

ApiFuture<T> pathCall<T>(
  HTTP http, {
  required String endpoint,
  required FutureOr<T> Function(dynamic body, int code) onResponseBody,
  required Map<String, dynamic> body,
  List<int> acceptableStatusCodes = const [200],
  String? Function(Response response)? onOtherStatus,
  Function(Object e)? onException,
  bool isDebug = false,
  bool nonJsonResponse = false,
}) {
  return apiCall(
    http,
    endpoint: endpoint,
    type: CallType.patch,
    onResponseBody: onResponseBody,
    acceptableStatusCodes: acceptableStatusCodes,
    body: body,
    onOtherStatus: onOtherStatus,
    onException: onException,
    isDebug: isDebug,
    nonJsonResponse: nonJsonResponse,
  );
}

ApiFuture<T> getCall<T>(
  HTTP http, {
  required String endpoint,
  required FutureOr<T> Function(dynamic body, int code) onResponseBody,
  List<int> acceptableStatusCodes = const [200],
  Map<String, String>? queryParameters,
  String? Function(Response response)? onOtherStatus,
  Function(Object e)? onException,
  bool isDebug = false,
  bool nonJsonResponse = false,
}) {
  return apiCall(
    http,
    endpoint: endpoint,
    type: CallType.get,
    onResponseBody: onResponseBody,
    acceptableStatusCodes: acceptableStatusCodes,
    queryParameters: queryParameters,
    onOtherStatus: onOtherStatus,
    onException: onException,
    isDebug: isDebug,
    nonJsonResponse: nonJsonResponse,
  );
}

ApiFuture<T> deleteCall<T>(
  HTTP http, {
  required String endpoint,
  required FutureOr<T> Function(dynamic body, int code) onResponseBody,
  List<int> acceptableStatusCodes = const [200, 204],
  required Map<String, dynamic> body,
  String? Function(Response response)? onOtherStatus,
  Function(Object e)? onException,
  bool isDebug = false,
  bool nonJsonResponse = false,
}) {
  return apiCall(
    http,
    endpoint: endpoint,
    type: CallType.delete,
    onResponseBody: onResponseBody,
    acceptableStatusCodes: acceptableStatusCodes,
    onOtherStatus: onOtherStatus,
    body: body,
    onException: onException,
    isDebug: isDebug,
    nonJsonResponse: nonJsonResponse,
  );
}

ApiFuture<T> apiCall<T>(
  HTTP http, {
  String? overrideBaseUrl,
  required String endpoint,
  required CallType type,
  required FutureOr<T> Function(dynamic body, int code) onResponseBody,
  String? Function(Response response)? onOtherStatus,
  Function(Object e)? onException,
  List<int> acceptableStatusCodes = const [200],
  Map<String, dynamic>? body,
  Map<String, String>? queryParameters,
  List<({String key, File file})>? files,
  List<({String key, Uint8List byte, String extension})>? bytes,
  bool isDebug = false,
  bool nonJsonResponse = false,
}) async {
  ApiFuture<T> function() async {
    final response = switch (type) {
      CallType.post => await http.post(
          endpoint,
          body: body!,
          overrideBaseUrl: overrideBaseUrl,
        ),
      CallType.get => await http.get(
          endpoint,
          queryParameters: queryParameters,
        ),
      CallType.put => await http.put(endpoint, body: body!),
      CallType.delete => await http.delete(endpoint, body: body!),
      CallType.patch => await http.patch(endpoint, body: body!),
      CallType.postWithFiles => await http.postWithFiles(
          endpoint,
          files: files!,
          body: Map<String, String>.from(body!),
        ),
      CallType.postWithBytes => await http.postWithBytes(
          endpoint,
          overrideBaseUrl: overrideBaseUrl,
          bytes: bytes!,
          body: Map<String, String>.from(body!),
        ),
    };

    final code = response.statusCode;
    if (acceptableStatusCodes.contains(code)) {
      final decodedBody = utf8.decode(response.bodyBytes);
      if (nonJsonResponse) {
        return Left(await onResponseBody(decodedBody, code));
      }
      return Left(await onResponseBody(jsonDecode(decodedBody), code));
    }

    if (onOtherStatus != null) {
      final string = onOtherStatus(response);
      if (string != null) {
        return right(FailureResponse(string));
      }
    }

    return handleOtherResponses(response);
  }

  if (isDebug) {
    return await function();
  }

  try {
    return await function();
  } on SocketException {
    onException?.call(const SocketException("No internet connection"));
    return const Right(InternetFailureResponse());
  } catch (e, s) {
    onException?.call(e);
    return Right(OtherFailureResponse("$e, $s"));
  }
}

Right<T, FailureResponse<E>> handleOtherResponses<T, E>(Response response) {
  String failureMessage = "Something went wrong";
  if (response.is400) {
    final body = Map.from(jsonDecode(response.body));
    failureMessage = body['error'] ?? "Something went wrong";
  }
  if (response.is401) {
    final body = Map.from(jsonDecode(response.body));
    failureMessage = body['detail'] ?? "Something went wrong";
  }
  if (response.is404) {
    final body = Map.from(jsonDecode(response.body));
    failureMessage = body['error'] ?? "Something went wrong";
  }
  return Right(OtherFailureResponse(failureMessage));
}
