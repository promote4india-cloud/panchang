import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../config/user_config.dart';
import '../../../assset/zodiac_icons.dart';
import '../../../providers/app_providers.dart';
import '../data/horoscope_api.dart';
import '../data/horoscope_cache.dart';
import '../models/horoscope_models.dart';

class HoroscopeState {
  final String activeDuration; 
  final String selectedZodiac; 
  final bool isChartLoading;   

  HoroscopeState({
    required this.activeDuration,
    required this.selectedZodiac,
    this.isChartLoading = false,
  });

  HoroscopeState copyWith({
    String? activeDuration,
    String? selectedZodiac,
    bool? isChartLoading,
  }) {
    return HoroscopeState(
      activeDuration: activeDuration ?? this.activeDuration,
      selectedZodiac: selectedZodiac ?? this.selectedZodiac,
      isChartLoading: isChartLoading ?? this.isChartLoading,
    );
  }
}

class HoroscopeNotifier extends Notifier<HoroscopeState> {
  @override
  HoroscopeState build() {
    return HoroscopeState(
      activeDuration: 'Daily',
      selectedZodiac: zodiacLabelFor(UserConfig.zodiacSign),
    );
  }

  void handleDurationChange(String duration) {
    state = state.copyWith(activeDuration: duration);
  }

  void handleZodiacSelection(String zodiac) {
    state = state.copyWith(selectedZodiac: zodiac);
  }

  Future<void> handleViewFullChartPressed() async {
    if (state.isChartLoading) return;
    state = state.copyWith(isChartLoading: true);
    
    // Simulate an API data fetch cycle
    await Future.delayed(const Duration(seconds: 2));
    
    state = state.copyWith(isChartLoading: false);
  }
}

final horoscopeProvider = NotifierProvider<HoroscopeNotifier, HoroscopeState>(() {
  return HoroscopeNotifier();
});

final horoscopeApiProvider = Provider<HoroscopeApiClient>((ref) {
  return HoroscopeApiClient(baseUrl: kApiBaseUrl);
});

final horoscopeQueryProvider = Provider<HoroscopeQuery>((ref) {
  final state = ref.watch(horoscopeProvider);
  final langCode = ref.watch(localeProvider).languageCode;
  return HoroscopeQuery(
    sign: _normalizeSign(state.selectedZodiac),
    period: _mapDurationToPeriod(state.activeDuration),
    language: langCode,
    tz: UserConfig.timezone,
  );
});

final horoscopeDetailsProvider = FutureProvider<HoroscopePredictionDto>((ref) async {
  final api = ref.read(horoscopeApiProvider);
  final cache = HoroscopeCache.instance;
  final query = ref.watch(horoscopeQueryProvider);

  final cached = cache.get(query.sign, query.period, query.language);
  if (cached != null) return cached;

  final result = await api.fetchHoroscope(query);
  cache.put(query.sign, query.period, query.language, result);
  _prefetchOtherPeriods(api, cache, query);
  return result;
});

/// Fire-and-forget background fetch of the other two standard periods for
/// the same sign.  Errors are silently swallowed — this is best-effort.
void _prefetchOtherPeriods(
  HoroscopeApiClient api,
  HoroscopeCache cache,
  HoroscopeQuery query,
) {
  for (final period in const ['daily', 'weekly', 'monthly']) {
    if (period == query.period) continue;
    if (cache.get(query.sign, period, query.language) != null) continue;
    final q = HoroscopeQuery(
      sign: query.sign,
      period: period,
      language: query.language,
      tz: query.tz,
    );
    api.fetchHoroscope(q).then((result) {
      cache.put(query.sign, period, query.language, result);
    }).catchError((_) {});
  }
}

String _normalizeSign(String value) => value.trim().toLowerCase();

String _mapDurationToPeriod(String value) {
  switch (value.toLowerCase()) {
    case 'weekly':
      return 'weekly';
    case 'monthly':
      return 'monthly';
    default:
      return 'daily';
  }
}

