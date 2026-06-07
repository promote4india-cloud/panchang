import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../config/app_config.dart';
import '../../../models/location_models.dart';
import '../models/panchang_models.dart';

const String kApiBaseUrl = AppConfig.apiBaseUrl;

class DashboardQuery {
  final String? date;
  final double lat;
  final double lon;
  final String tz;
  final String language;

  DashboardQuery({
    this.date,
    required this.lat,
    required this.lon,
    required this.tz,
    required this.language,
  });

  Map<String, String> toQueryParams() {
    return {
      if (date != null) 'date': date!,
      'lat': lat.toStringAsFixed(4),
      'lon': lon.toStringAsFixed(4),
      'tz': tz,
      'language': language,
    };
  }
}

class PanchangApiClient {
  final String baseUrl;
  final http.Client _client;

  PanchangApiClient({required this.baseUrl, http.Client? client})
    : _client = client ?? http.Client();

  Future<PanchangTodayDto> fetchPanchangToday(DashboardQuery query) async {
    final json = await _getJson('/v1/panchang/today', query.toQueryParams());
    return PanchangTodayDto.fromJson(json);
  }

  Future<PanchangTodayDto> fetchPanchang(DashboardQuery query) async {
    final json = await _getJson('/v1/panchang', query.toQueryParams());
    return PanchangTodayDto.fromJson(json);
  }

  Future<MuhuratBundleDto> fetchMuhurat(DashboardQuery query) async {
    final json = await _getJson('/v1/muhurat', query.toQueryParams());
    return MuhuratBundleDto.fromJson(json);
  }

  Future<MuhuratDetailDto> fetchMuhuratDetail(
    String muhuratId,
    DashboardQuery query,
  ) async {
    final json = await _getJson('/v1/muhurat/$muhuratId', query.toQueryParams());
    return MuhuratDetailDto.fromJson(json);
  }

  Future<FestivalsTodayResponseDto> fetchFestivalsToday(
    DashboardQuery query,
  ) async {
    final json = await _getJson('/v1/festivals/today', query.toQueryParams());
    return FestivalsTodayResponseDto.fromJson(json);
  }

  Future<FestivalsUpcomingResponseDto> fetchUpcomingFestivals(
    DashboardQuery query, {
    String window = '7d',
  }) async {
    final params = {...query.toQueryParams(), 'window': window};
    final json = await _getJson('/v1/festivals/upcoming', params);
    return FestivalsUpcomingResponseDto.fromJson(json);
  }

  Future<FestivalCalendarResponseDto> fetchFestivalsCalendar(
    DashboardQuery query, {
    required int year,
    required int month,
    bool includeContent = false,
  }) async {
    final params = {
      ...query.toQueryParams(),
      'year': year.toString(),
      'month': month.toString(),
      if (includeContent) 'include_content': '1',
    };
    final json = await _getJson('/v1/festivals/calendar', params);
    return FestivalCalendarResponseDto.fromJson(json);
  }

  Future<HoroscopeDailyDto> fetchDailyHoroscope(
    String sign,
    DashboardQuery query,
  ) async {
    final params = {
      if (query.date != null) 'date': query.date!,
      'period': 'daily',
      'tz': query.tz,
      'language': query.language,
    };
    final json = await _getJson('/v1/horoscope/$sign', params);
    return HoroscopeDailyDto.fromJson(json);
  }

  Future<FestivalDatesResponseDto> fetchFestivalDates(
    String festivalId,
    DashboardQuery query, {
    required int year,
    bool includeChildren = true,
    String tradition = 'all',
    String ayanamsa = 'lahiri',
    String calendarTime = 'civil',
  }) async {
    final params = {
      ...query.toQueryParams(),
      'year': year.toString(),
      'include_children': includeChildren ? 'true' : 'false',
      'tradition': tradition,
      'ayanamsa': ayanamsa,
      'calendar_time': calendarTime,
    };
    final json = await _getJson('/v1/festivals/$festivalId/dates', params);
    return FestivalDatesResponseDto.fromJson(json);
  }

  /// Reverse-geocode GPS coordinates to the nearest city + IANA timezone.
  /// Calls GET /v1/locations/resolve?lat=&lon=&language=
  Future<LocationResolveResult> resolveLocation({
    required double lat,
    required double lon,
    String language = 'en',
  }) async {
    final params = {
      'lat': lat.toStringAsFixed(6),
      'lon': lon.toStringAsFixed(6),
      'language': language,
    };
    final json = await _getJson('/v1/locations/resolve', params);
    return LocationResolveResult.fromJson(json);
  }

  Future<List<LocationSearchResult>> searchLocations({
    required String query,
    String country = 'IN',
    String language = 'en',
    int limit = 10,
  }) async {
    final params = {
      'q': query,
      'country': country,
      'language': language,
      'limit': limit.toString(),
      'include_small': 'false',
    };
    final json = await _getJson('/v1/locations/search', params);
    final results = json['results'] as List<dynamic>? ?? [];
    return results
        .map(
          (item) => LocationSearchResult.fromJson(item as Map<String, dynamic>),
        )
        .toList();
  }

  Future<Map<String, dynamic>> _getJson(
    String path,
    Map<String, String> params,
  ) async {
    final uri = Uri.parse(baseUrl).replace(path: path, queryParameters: params);
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
      throw ApiException(
        'Request failed: ${response.statusCode}',
        response.body,
      );
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}

class ApiException implements Exception {
  final String message;
  final String? body;

  ApiException(this.message, [this.body]);

  @override
  String toString() => body == null ? message : '$message\n$body';
}
