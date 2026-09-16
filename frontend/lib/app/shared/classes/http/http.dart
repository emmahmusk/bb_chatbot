import 'dart:convert';
import 'dart:developer';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/app/modules/auth/data/login_response_model.dart';
import 'package:frontend/app/shared/classes/preferences/preferences.dart';
import 'package:frontend/app/shared/classes/preferences/preferences_strings.dart';
import 'package:http/http.dart' as http;


final httpProvider = Provider<HTTP>((ref) {
  return HTTP();
});

class HTTP {
  String get baseUrl {
    return _baseUrl;
  }

  final Map<String, String> _headers = Map<String, String>.from(
    {
      'Content-type': 'application/json',
      'Accept': 'application/json',
    },
  );

  String _baseUrl = "";
  String _chatbotBaseUrl = "";

  void setBaseUrl(String url) {
    _baseUrl = url;
  }

  String get chatbotBaseUrl => _chatbotBaseUrl;

  void setChatbotBaseUrl(String url) {
    _chatbotBaseUrl = url;
  }

  Map<String, String> get getHeaders {
    return Map<String, String>.from(_headers);
  }

  List<String> headerLog = [];

  String? getToken() {
    return getHeaders["Authorization"]?.split(" ").last;
  }

  void removeToken() {
    removeHeader("Authorization");
  }

  void addTokenFromCache() {
    try {
      final model = Preferences.getModel(
        key: PreferencesStrings.loginResponseModel,
        creator: (map) => LoginResponseModel.fromJson(map),
      );
      if (model != null) {
        final token = model.access;
        addHeader(key: "Authorization", value: "Bearer $token");
      }
    } catch (e) {
      return;
    }
  }

  addHeader({
    required String key,
    required String value,
  }) {
    _headers[key] = value;
    headerLog.add("Added $key: $value");
  }

  removeHeader(String key) {
    _headers.remove(key);

    headerLog.add("Removed $key");
  }

  Future<http.Response> post(
    String endpoint, {
    String? overrideBaseUrl,
    bool endsWithSlash = true,
    required Map<String, dynamic> body,
  }) async {
    addTokenFromCache();
    final myBaseUrl = overrideBaseUrl ?? baseUrl;
    String url = "$myBaseUrl/$endpoint";
    if (endsWithSlash) {
      url += "/";
    }
    final response = await http.post(
      Uri.parse(url),
      headers: getHeaders,
      body: jsonEncode(body),
    );
    return response;
  }

  Future<http.Response> postWithList(
    String endpoint, {
    required List<Map<String, dynamic>> body,
  }) async {
    addTokenFromCache();

    String url = "$baseUrl/$endpoint/";
    final response = await http.post(
      Uri.parse(url),
      headers: getHeaders,
      body: jsonEncode(body),
    );

    return response;
  }

  Future<http.Response> postWithBytes(
    String endpoint, {
    String? overrideBaseUrl,
    bool endsWithSlash = true,
    required Map<String, String> body,
    required List<({String key, Uint8List byte, String extension})> bytes,
  }) async {
    addTokenFromCache();

    final myBaseUrl = overrideBaseUrl ?? baseUrl;
    String url = "$myBaseUrl/$endpoint";
    if (endsWithSlash) {
      url += "/";
    }
    final request = http.MultipartRequest('POST', Uri.parse(url));
    request.headers
        .addAll(getHeaders..["Content-Type"] = "multipart/form-data");

    for (final byte in bytes) {
      request.files.add(
        http.MultipartFile.fromBytes(
          byte.key,
          byte.byte,
          filename: "${byte.key}.${byte.extension}",
        ),
      );
    }
    request.fields.addAll(body);
    final response = await request.send();
    return http.Response.fromStream(response);
  }

  Future<http.Response> postWithFile(
    String endpoint, {
    required String fileKey,
    required File file,
    required Map<String, String> body,
  }) async {
    addTokenFromCache();
    String url = "$baseUrl/$endpoint/";
    final request = http.MultipartRequest('POST', Uri.parse(url));
    request.headers.addAll(getHeaders);
    request.files.add(
      await http.MultipartFile.fromPath(
        fileKey,
        file.path,
      ),
    );
    request.fields.addAll(body);
    final response = await request.send();
    return http.Response.fromStream(response);
  }

  Future<http.Response> postWithFiles(
    String endpoint, {
    required List<({String key, File file})> files,
    required Map<String, String> body,
  }) async {
    addTokenFromCache();
    String url = "$baseUrl/$endpoint/";
    final request = http.MultipartRequest('POST', Uri.parse(url));
    request.headers.addAll(getHeaders);
    for (final (key: key, file: file) in files) {
      final fileField = await http.MultipartFile.fromPath(
        key,
        file.path,
      );
      request.files.add(fileField);
    }

    request.fields.addAll(body);

    final response = await request.send();
    return http.Response.fromStream(response);
  }

  Future<http.Response> get(
    String endpoint, {
    String? overrideBaseUrl,
    Map<String, String>? queryParameters,
    bool endsWithSlash = true,
  }) async {
    addTokenFromCache();
    final myBaseUrl = overrideBaseUrl ?? baseUrl;
    String url = "$myBaseUrl/$endpoint";
    // if (endsWithSlash) {
    //   url += "/";
    // }
    if (queryParameters != null) {
      url += "?";
      for (final value in queryParameters.entries) {
        url += "${value.key}=${value.value}&";
      }
      url = url.substring(0, url.length - 1);
      log(' URL: $url');
    }
    final response = await http.get(
      Uri.parse(url),
      headers: getHeaders,
    );

    return response;
  }

  Future<http.Response> put(
    String endpoint, {
    required Map<String, dynamic> body,
  }) async {
    addTokenFromCache();
    String url = "$baseUrl/$endpoint/";
    final response = await http.put(
      Uri.parse(url),
      headers: getHeaders,
      body: jsonEncode(body),
    );
    return response;
  }

  Future<http.Response> patch(
    String endpoint, {
    required Map<String, dynamic> body,
  }) async {
    addTokenFromCache();
    String url = "$baseUrl/$endpoint/";
    final response = await http.patch(
      Uri.parse(url),
      headers: getHeaders,
      body: jsonEncode(body),
    );
    return response;
  }

  Future<http.Response> delete(
    String endpoint, {
    Map<String, dynamic>? body,
  }) async {
    addTokenFromCache();
    String url = "$baseUrl/$endpoint/";
    final response = await http.delete(
      Uri.parse(url),
      headers: getHeaders,
      body: body == null ? null : jsonEncode(body),
    );
    return response;
  }
}
