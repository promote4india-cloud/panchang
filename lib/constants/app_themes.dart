import 'package:flutter/material.dart';
import 'app_colors.dart';

class AppThemes {
  // --- Epilogue Font Family Styles (Headlines & Labels) ---
  static const TextStyle display = TextStyle(
    fontFamily: 'Epilogue',
    fontSize: 48,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.96, // Matches tailwind "-0.02em"
    color: AppColors.onSurface,
  );

  static const TextStyle headlineLg = TextStyle(
    fontFamily: 'Epilogue',
    fontSize: 32,
    fontWeight: FontWeight.w600,
    height: 1.2,
    color: AppColors.onSurface,
  );

  static const TextStyle headlineLgMobile = TextStyle(
    fontFamily: 'Epilogue',
    fontSize: 28,
    fontWeight: FontWeight.w600,
    height: 1.2,
    color: AppColors.onSurface,
  );

  static const TextStyle headlineMd = TextStyle(
    fontFamily: 'Epilogue',
    fontSize: 24,
    fontWeight: FontWeight.w600,
    height: 1.3,
    color: AppColors.primary,
  );

  // ADDED HERE: headlineSm style for profile/headers
  static const TextStyle headlineSm = TextStyle(
    fontFamily: 'Epilogue',
    fontSize: 20,
    fontWeight: FontWeight.w600,
    height: 1.4,
    color: AppColors.onSurface,
  );

  // --- Manrope Font Family Styles (Body Copy & Metadata) ---
  static const TextStyle bodyLg = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 18,
    fontWeight: FontWeight.w400,
    height: 1.6,
    color: AppColors.onSurface,
  );

  static const TextStyle bodyMd = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 16,
    fontWeight: FontWeight.w400,
    height: 1.6,
    color: AppColors.onSurfaceVariant,
  );

  // ADDED HERE: bodySm style for secondary descriptions
  static const TextStyle bodySm = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 1.4,
    color: AppColors.onSurfaceVariant,
  );

  static const TextStyle labelMd = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 14,
    fontWeight: FontWeight.w600,
    height: 1.4,
    letterSpacing: 0.7, // Matches tailwind "0.05em"
    color: AppColors.onSurfaceVariant,
  );

  // ADDED HERE: labelLg style for uppercase group headers
  static const TextStyle labelLg = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 14,
    fontWeight: FontWeight.w600,
    height: 1.1,
    letterSpacing: 0.7,
    color: AppColors.primaryContainer,
  );
}