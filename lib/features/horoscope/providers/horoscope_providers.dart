import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../config/user_config.dart';
import '../../../assset/zodiac_icons.dart';
import '../data/horoscope_api.dart';
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
  return HoroscopeQuery(
    sign: _normalizeSign(state.selectedZodiac),
    period: _mapDurationToPeriod(state.activeDuration),
    language: UserConfig.language,
    tz: UserConfig.timezone,
  );
});

final horoscopeDetailsProvider = FutureProvider<HoroscopePredictionDto>((ref) async {
  final api = ref.read(horoscopeApiProvider);
  final query = ref.watch(horoscopeQueryProvider);
  return api.fetchHoroscope(query);
});

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

