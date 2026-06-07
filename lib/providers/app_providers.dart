import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// =========================================================================
// NAVIGATION STATE MANAGER
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
// LOCALE / LANGUAGE STATE MANAGER
// Maps backend language codes (en, hi, bn, …) to Flutter Locale objects.
// =========================================================================

/// All language codes supported by both the backend and the UI.
const List<_LangOption> kSupportedLanguages = [
  _LangOption('en', 'EN', 'English'),
  _LangOption('hi', 'HI', 'हिन्दी'),
  _LangOption('bn', 'BN', 'বাংলা'),
  _LangOption('ta', 'TA', 'தமிழ்'),
  _LangOption('te', 'TE', 'తెలుగు'),
  _LangOption('mr', 'MR', 'मराठी'),
  _LangOption('gu', 'GU', 'ગુજરાતી'),
  _LangOption('kn', 'KN', 'ಕನ್ನಡ'),
  _LangOption('ml', 'ML', 'മലയാളം'),
  _LangOption('pa', 'PA', 'ਪੰਜਾਬੀ'),
  _LangOption('sa', 'SA', 'संस्कृत'),
  _LangOption('or', 'OR', 'ଓଡ଼ିଆ'),
];

class _LangOption {
  final String code;   // Backend/ARB code
  final String short;  // Button label (2–3 chars)
  final String label;  // Full name shown in picker
  const _LangOption(this.code, this.short, this.label);
}

class LocaleNotifier extends Notifier<Locale> {
  @override
  Locale build() => const Locale('en');

  void setLocale(Locale locale) => state = locale;

  void setByCode(String code) => state = Locale(code);
}

final localeProvider = NotifierProvider<LocaleNotifier, Locale>(() {
  return LocaleNotifier();
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

  /// Shows a bottom-sheet language picker and updates both the locale
  /// provider and [UserConfig] so every API call re-fires in the new language.
  void handleLanguagePressed(BuildContext context, WidgetRef ref) {
    showModalBottomSheet<void>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 12),
              Container(
                width: 40, height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Select Language',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              ...kSupportedLanguages.map((lang) {
                final currentCode = ref.read(localeProvider).languageCode;
                final isSelected = currentCode == lang.code;
                return ListTile(
                  leading: Text(
                    lang.short,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: isSelected ? Theme.of(ctx).colorScheme.primary : null,
                    ),
                  ),
                  title: Text(lang.label),
                  trailing: isSelected
                      ? Icon(Icons.check, color: Theme.of(ctx).colorScheme.primary)
                      : null,
                  onTap: () {
                    ref.read(localeProvider.notifier).setByCode(lang.code);
                    state = state.copyWith(selectedLanguage: lang.label);
                    Navigator.of(ctx).pop();
                  },
                );
              }),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );
  }
}

final topBarProvider = NotifierProvider<TopBarNotifier, TopBarState>(() {
  return TopBarNotifier();
});

// =========================================================================
// APP THEME MODE STATE MANAGER
// =========================================================================
class ThemeModeNotifier extends Notifier<ThemeMode> {
  @override
  ThemeMode build() => ThemeMode.system;

  void setThemeMode(ThemeMode mode) {
    state = mode;
  }
}

final themeModeProvider = NotifierProvider<ThemeModeNotifier, ThemeMode>(() {
  return ThemeModeNotifier();
});