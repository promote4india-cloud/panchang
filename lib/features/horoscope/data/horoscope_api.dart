import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../config/app_config.dart';
import '../models/horoscope_models.dart';

const String kApiBaseUrl = AppConfig.apiBaseUrl;

class HoroscopeQuery {
  final String sign;
  final String period;
  final String language;
  final String tz;
  final String? date;

  HoroscopeQuery({
    required this.sign,
    required this.period,
    required this.language,
    required this.tz,
    this.date,
  });

  Map<String, String> toQueryParams() {
    return {
      if (date != null) 'date': date!,
      'period': period,
      'language': language,
      'tz': tz,
    };
  }
}

class HoroscopeApiClient {
  final String baseUrl;
  final http.Client _client;

  HoroscopeApiClient({
    required this.baseUrl,
    http.Client? client,
  }) : _client = client ?? http.Client();

  Future<HoroscopePredictionDto> fetchHoroscope(HoroscopeQuery query) async {
    final uri = Uri.parse(baseUrl).replace(
      path: '/v1/horoscope/${query.sign}',
      queryParameters: query.toQueryParams(),
    );
    final response = await _client
        .get(uri, headers: AppConfig.authHeaders)
        .timeout(const Duration(seconds: 30));
    if (response.statusCode == 401 || response.statusCode == 403) {
      throw ApiException(
        'Authentication failed (${response.statusCode}) — '
        'check PANCHANG_USER_API_KEY build config.',
        response.body,
      );
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException('Request failed: ${response.statusCode}', response.body);
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return HoroscopePredictionDto.fromJson(json);
  }
}

class ApiException implements Exception {
  final String message;
  final String? body;

  ApiException(this.message, [this.body]);

  @override
  String toString() => body == null ? message : '$message\n$body';
}
