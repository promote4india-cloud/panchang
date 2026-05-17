import 'package:flutter_riverpod/flutter_riverpod.dart';

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
    return HoroscopeState(activeDuration: 'Daily', selectedZodiac: 'Aries');
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