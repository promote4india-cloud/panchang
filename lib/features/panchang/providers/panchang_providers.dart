import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../config/app_config.dart';
import '../../../config/user_config.dart';
import '../../../assset/zodiac_icons.dart';
import '../../../providers/user_location_provider.dart';
import '../data/panchang_api.dart';
import '../models/panchang_models.dart';

final panchangApiProvider = Provider<PanchangApiClient>((ref) {
  return PanchangApiClient(baseUrl: kApiBaseUrl);
});

final dashboardQueryProvider = Provider<DashboardQuery>((ref) {
  final location = ref.watch(userLocationProvider).value;
  return DashboardQuery(
    lat: location?.latitude ?? UserConfig.latitude,
    lon: location?.longitude ?? UserConfig.longitude,
    tz: UserConfig.timezone,
    language: UserConfig.language,
  );
});

final panchangDashboardProvider = FutureProvider<PanchangDashboardVm>((ref) async {
  final api = ref.read(panchangApiProvider);
  final query = ref.read(dashboardQueryProvider);

  final results = await Future.wait([
    api.fetchPanchangToday(query),
    api.fetchMuhurat(query),
    api.fetchFestivalsToday(query),
    api.fetchUpcomingFestivals(query),
    api.fetchDailyHoroscope(UserConfig.zodiacSign, query),
  ]);

  final panchang = results[0] as PanchangTodayDto;
  final muhurat = results[1] as MuhuratBundleDto;
  final festivalsToday = results[2] as FestivalsTodayResponseDto;
  final upcoming = results[3] as FestivalsUpcomingResponseDto;
  final horoscope = results[4] as HoroscopeDailyDto;

  final visibleToday = festivalsToday.festivals
      .where((item) => !_isIslamicType(item.type))
      .toList();
  final visibleUpcoming = upcoming.items
      .where((item) => !_isIslamicType(item.type))
      .toList();

    final auspiciousList = muhurat.muhurats
      .where((item) => _isAuspiciousCategory(item.category))
      .map((item) => PanchangMuhuratVm(
            name: item.name,
            timeRange: _formatRange(item.start, item.end),
          ))
      .toList();
    final inauspiciousList = muhurat.muhurats
      .where((item) => _isInauspiciousCategory(item.category))
      .map((item) => PanchangMuhuratVm(
            name: item.name,
            timeRange: _formatRange(item.start, item.end),
          ))
      .toList();

  final festivalTitle = visibleToday.isNotEmpty
      ? visibleToday.first.name
      : '';
      // : 'No festival today';

  final upcomingItem = _firstOrNull(visibleUpcoming);

  return PanchangDashboardVm(
    dateLabel: _formatDateLabel(panchang.date, panchang.weekday),
    lunarLabel: '${panchang.masa.name} ${panchang.tithi.paksha} ${panchang.tithi.name}',
    festivalTitle: festivalTitle,
    tithiLabel: panchang.tithi.name,
    nakshatraLabel: panchang.nakshatra.name,
    sunriseLabel: _formatTime(panchang.sunMoon.sunriseLocal),
    sunsetLabel: _formatTime(panchang.sunMoon.sunsetLocal),
    auspiciousMuhurats: auspiciousList,
    inauspiciousMuhurats: inauspiciousList,
    rashifalSign: zodiacLabelFor(horoscope.sign.isEmpty
      ? UserConfig.zodiacSign
      : horoscope.sign),
    rashifalText: horoscope.prediction?.trim().isNotEmpty == true
      ? horoscope.prediction!
      : 'No horoscope available for today.',
    rashifalSymbol: zodiacSymbolFor(horoscope.sign.isEmpty
      ? UserConfig.zodiacSign
      : horoscope.sign),
    upcomingDateLabel: upcomingItem == null
        ? '--'
        : _formatShortDate(upcomingItem.date, upcomingItem.weekday),
    upcomingName: upcomingItem?.name ?? 'No upcoming events',
  );
});

T? _firstOrNull<T>(List<T> items) => items.isEmpty ? null : items.first;

bool _isIslamicType(String? value) {
  if (value == null || value.isEmpty) return false;
  final normalized = value.toLowerCase();
  return normalized.contains('islamic') || normalized.contains('muslim');
}

bool _isAuspiciousCategory(String? value) {
  if (value == null || value.isEmpty) return false;
  return value.toLowerCase() == 'auspicious';
}

bool _isInauspiciousCategory(String? value) {
  if (value == null || value.isEmpty) return false;
  return value.toLowerCase() == 'inauspicious';
}


String _formatRange(String? start, String? end) {
  if (start == null || end == null) return '--';
  return '${_formatTime(start)} - ${_formatTime(end)}';
}

String _formatTime(String? value) {
  if (value == null || value.isEmpty) return '--';

  int? hour;
  int? minute;
  if (value.contains('T')) {
    final timePart = value.split('T').last;
    final trimmed = timePart.split(RegExp(r'[+Z-]')).first;
    final parts = trimmed.split(':');
    if (parts.length >= 2) {
      hour = int.tryParse(parts[0]);
      minute = int.tryParse(parts[1]);
    }
  } else if (value.contains(':')) {
    final parts = value.split(':');
    if (parts.length >= 2) {
      hour = int.tryParse(parts[0]);
      minute = int.tryParse(parts[1]);
    }
  }

  if (hour == null || minute == null) return value;

  var displayHour = hour % 12;
  if (displayHour == 0) displayHour = 12;
  final minuteLabel = minute.toString().padLeft(2, '0');
  final suffix = hour >= 12 ? 'PM' : 'AM';
  return '$displayHour:$minuteLabel $suffix';
}

String _formatDateLabel(String date, String weekday) {
  final parsed = DateTime.tryParse(date);
  if (parsed == null) return '$date | $weekday';
  return '${parsed.day} ${_monthName(parsed.month)} ${parsed.year} | $weekday';
}

String _formatShortDate(String date, String? weekday) {
  final parsed = DateTime.tryParse(date);
  if (parsed == null) return date;
  final day = parsed.day.toString().padLeft(2, '0');
  final month = _monthShort(parsed.month);
  final label = '$month $day';
  if (weekday == null || weekday.isEmpty) return label;
  return '$label\n$weekday';
}

String _monthName(int month) {
  const months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];
  return months[(month - 1).clamp(0, 11)];
}

String _monthShort(int month) {
  const months = [
    'JAN',
    'FEB',
    'MAR',
    'APR',
    'MAY',
    'JUN',
    'JUL',
    'AUG',
    'SEP',
    'OCT',
    'NOV',
    'DEC',
  ];
  return months[(month - 1).clamp(0, 11)];
}
