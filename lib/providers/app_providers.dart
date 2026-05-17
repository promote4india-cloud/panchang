import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// =========================================================================
// ADDED: NAVIGATION TIMING & TAB STATE MANAGER
// =========================================================================
class NavigationNotifier extends Notifier<int> {
  @override
  int build() => 0; // Default index: 0 (Panchang)

  void changeTab(int newIndex) {
    state = newIndex;
  }
}

final navigationProvider = NotifierProvider<NavigationNotifier, int>(() {
  return NavigationNotifier();
});

// =========================================================================
// TOP BAR STATE & NOTIFIER
// =========================================================================
class TopBarState {
  final String selectedLanguage; // e.g., 'English', 'Hindi'
  final String currentRegion;    // e.g., 'Bengaluru, IN'

  TopBarState({required this.selectedLanguage, required this.currentRegion});

  TopBarState copyWith({String? selectedLanguage, String? currentRegion}) {
    return TopBarState(
      selectedLanguage: selectedLanguage ?? this.selectedLanguage,
      currentRegion: currentRegion ?? this.currentRegion,
    );
  }
}

class TopBarNotifier extends Notifier<TopBarState> {
  @override
  TopBarState build() {
    return TopBarState(selectedLanguage: 'English', currentRegion: 'Detecting...');
  }

  // --- MENU ONPRESSED ---
  void handleMenuPressed(BuildContext context) {
    // Logic for side-drawer goes here
  }

  // --- LANGUAGE ONPRESSED ---
  void handleLanguagePressed() {
    final nextLang = state.selectedLanguage == 'English' ? 'Hindi' : 'English';
    state = state.copyWith(selectedLanguage: nextLang);
  }
}

final topBarProvider = NotifierProvider<TopBarNotifier, TopBarState>(() {
  return TopBarNotifier();
});