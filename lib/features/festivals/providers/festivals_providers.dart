import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../panchang/data/panchang_api.dart';
import '../../panchang/models/panchang_models.dart';
import '../../panchang/providers/panchang_providers.dart';
import '../data/spiritual_tips.dart';

class FestivalCalendarEventVm {
  final String id;
  final DateTime date;
  final String weekday;
  final String name;
  final String? type;
  final FestivalContentDto? content;
  final List<String> rituals;
  final List<FestivalFaqDto> faqs;

  FestivalCalendarEventVm({
    required this.id,
    required this.date,
    required this.weekday,
    required this.name,
    required this.type,
    required this.content,
    required this.rituals,
    required this.faqs,
  });
}

class FestivalsCalendarVm {
  final int year;
  final int month;
  final String monthLabel;
  final String masaRangeLabel;
  final List<FestivalCalendarDayDto> days;
  final List<FestivalCalendarEventVm> events;

  FestivalsCalendarVm({
    required this.year,
    required this.month,
    required this.monthLabel,
    required this.masaRangeLabel,
    required this.days,
    required this.events,
  });
}

final festivalsCalendarProvider = FutureProvider<FestivalsCalendarVm>((
  ref,
) async {
  final api = ref.read(panchangApiProvider);
  final baseQuery = ref.read(dashboardQueryProvider);
  final activeMonth = ref.watch(festivalMonthProvider);

  final startDate = DateTime(activeMonth.year, activeMonth.month, 1);
  final endDate = DateTime(activeMonth.year, activeMonth.month + 1, 0);

  final results = await Future.wait([
    api.fetchPanchang(_queryForDate(baseQuery, startDate)),
    api.fetchPanchang(_queryForDate(baseQuery, endDate)),
    api.fetchFestivalsCalendar(
      baseQuery,
      year: activeMonth.year,
      month: activeMonth.month,
      includeContent: true,
    ),
  ]);

  final startPanchang = results[0] as PanchangTodayDto;
  final endPanchang = results[1] as PanchangTodayDto;
  final calendar = results[2] as FestivalCalendarResponseDto;

  final filteredDays = calendar.days
      .map(
        (day) => FestivalCalendarDayDto(
          day: day.day,
          weekday: day.weekday,
          events: day.events
              .where((event) => !_isIslamicType(event.type))
              .toList(),
        ),
      )
      .toList();

  final events = <FestivalCalendarEventVm>[];
  for (final day in filteredDays) {
    for (final event in day.events) {
      events.add(
        FestivalCalendarEventVm(
          id: event.id,
          date: DateTime(calendar.year, calendar.month, day.day),
          weekday: day.weekday,
          name: event.name,
          type: event.type,
          content: event.content,
          rituals: event.rituals,
          faqs: event.faqs,
        ),
      );
    }
  }

  events.sort((a, b) => a.date.compareTo(b.date));

  final monthLabel = '${_monthName(calendar.month)} ${calendar.year}';
  final startPurnimanta = _stripAdhik(
    startPanchang.hinduMonthAndYear.monthPurnimanta,
  );
  final startAmanta = _stripAdhik(startPanchang.hinduMonthAndYear.monthAmanta);
  final endPurnimanta = _stripAdhik(
    endPanchang.hinduMonthAndYear.monthPurnimanta,
  );
  final endAmanta = _stripAdhik(endPanchang.hinduMonthAndYear.monthAmanta);
  final masaRangeLabel =
      'MASA: $startPurnimanta/$startAmanta - $endPurnimanta/$endAmanta';

  return FestivalsCalendarVm(
    year: calendar.year,
    month: calendar.month,
    monthLabel: monthLabel,
    masaRangeLabel: masaRangeLabel,
    days: filteredDays,
    events: events,
  );
});

final spiritualTipProvider = FutureProvider<String>((ref) async {
  final api = ref.read(panchangApiProvider);
  final query = ref.read(dashboardQueryProvider);
  final panchang = await api.fetchPanchangToday(query);

  final monthName = panchang.hinduMonthAndYear.monthPurnimanta.isNotEmpty
      ? panchang.hinduMonthAndYear.monthPurnimanta
      : panchang.masa.name;

  return spiritualTipForHinduMonth(monthName);
});

class FestivalMonthNotifier extends Notifier<DateTime> {
  @override
  DateTime build() {
    final now = DateTime.now();
    return DateTime(now.year, now.month, 1);
  }

  void setMonth(DateTime date) {
    state = DateTime(date.year, date.month, 1);
  }
}

final festivalMonthProvider = NotifierProvider<FestivalMonthNotifier, DateTime>(
  () {
    return FestivalMonthNotifier();
  },
);

DashboardQuery _queryForDate(DashboardQuery baseQuery, DateTime date) {
  return DashboardQuery(
    date: _formatIsoDate(date),
    lat: baseQuery.lat,
    lon: baseQuery.lon,
    tz: baseQuery.tz,
    language: baseQuery.language,
  );
}

String _formatIsoDate(DateTime date) {
  final year = date.year.toString().padLeft(4, '0');
  final month = date.month.toString().padLeft(2, '0');
  final day = date.day.toString().padLeft(2, '0');
  return '$year-$month-$day';
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

bool _isIslamicType(String? value) {
  if (value == null || value.isEmpty) return false;
  final normalized = value.toLowerCase();
  return normalized.contains('islamic') || normalized.contains('muslim');
}

String _stripAdhik(String value) {
  return value.replaceAll(' (Adhik)', '').trim();
}
