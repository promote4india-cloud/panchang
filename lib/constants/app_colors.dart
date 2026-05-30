import 'package:flutter/material.dart';

class AppColors {
  // ─── Light palette (unchanged originals) ───
  static const Color primary = Color(0xFF9B4600);
  static const Color primaryContainer = Color(0xFFFF7700);
  static const Color onPrimaryContainer = Color(0xFF5B2600);
  static const Color onSurface = Color.fromARGB(255, 35, 36, 36);
  static const Color onSurfaceVariant = Color(0xFF584235);
  static const Color surface = Color(0xFFFBF9F8);
  static const Color outlineVariant = Color(0xFFE0C0B0);
  static const Color error = Color(0xFFBA1A1A);
  static const Color errorContainerBg = Color(0xFFFFDAD6);

  // ─── Dark palette ───
  static const Color primaryDark = Color(0xFFFFB07A);
  static const Color primaryContainerDark = Color(0xFFFF8C3A);
  static const Color onPrimaryContainerDark = Color(0xFFFFDCC5);
  static const Color onSurfaceDark = Color(0xFFE6E1DE);
  static const Color onSurfaceVariantDark = Color(0xFFB8A99E);
  static const Color surfaceDark = Color(0xFF111111);
  static const Color outlineVariantDark = Color(0xFF3D3330);
  static const Color errorDark = Color(0xFFFFB4AB);
  static const Color errorContainerBgDark = Color(0xFF3B1010);

  // ─── Card / container surfaces ───
  static const Color cardLight = Colors.white;
  static const Color cardDark = Color(0xFF1E1E1E);
  static const Color cardElevatedDark = Color(0xFF252525);
}

/// Theme-aware color accessor — obtain via `AppColorsOf(context)`.
class AppColorsOf {
  final Brightness brightness;
  AppColorsOf._(this.brightness);

  factory AppColorsOf(BuildContext context) {
    return AppColorsOf._(Theme.of(context).brightness);
  }

  bool get isDark => brightness == Brightness.dark;

  Color get primary => isDark ? AppColors.primaryDark : AppColors.primary;
  Color get primaryContainer =>
      isDark ? AppColors.primaryContainerDark : AppColors.primaryContainer;
  Color get onPrimaryContainer =>
      isDark ? AppColors.onPrimaryContainerDark : AppColors.onPrimaryContainer;
  Color get onSurface =>
      isDark ? AppColors.onSurfaceDark : AppColors.onSurface;
  Color get onSurfaceVariant =>
      isDark ? AppColors.onSurfaceVariantDark : AppColors.onSurfaceVariant;
  Color get surface => isDark ? AppColors.surfaceDark : AppColors.surface;
  Color get outlineVariant =>
      isDark ? AppColors.outlineVariantDark : AppColors.outlineVariant;
  Color get error => isDark ? AppColors.errorDark : AppColors.error;
  Color get errorContainerBg =>
      isDark ? AppColors.errorContainerBgDark : AppColors.errorContainerBg;
  Color get card => isDark ? AppColors.cardDark : AppColors.cardLight;
  Color get cardElevated =>
      isDark ? AppColors.cardElevatedDark : AppColors.cardLight;

  /// Subtle tinted background for chips / muhurat cards.
  Color get subtleBg =>
      isDark ? Colors.white.withOpacity(0.06) : Colors.black.withOpacity(0.03);
  /// Border color (thin outline around cards)
  Color get border =>
      isDark ? Colors.white.withOpacity(0.08) : AppColors.outlineVariant.withOpacity(0.3);
}