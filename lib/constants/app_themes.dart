import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

class AppThemes {
  // --- Epilogue Font Family Styles (Headlines & Labels) ---
  static final TextStyle display = GoogleFonts.epilogue(
    fontSize: 48,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.96, // Matches tailwind "-0.02em"
    color: AppColors.onSurface,
  );

  static final TextStyle headlineLg = GoogleFonts.epilogue(
    fontSize: 32,
    fontWeight: FontWeight.w600,
    height: 1.2,
    color: AppColors.onSurface,
  );

  static final TextStyle headlineLgMobile = GoogleFonts.epilogue(
    fontSize: 28,
    fontWeight: FontWeight.w600,
    height: 1.2,
    color: AppColors.onSurface,
  );

  static final TextStyle headlineMd = GoogleFonts.epilogue(
    fontSize: 24,
    fontWeight: FontWeight.w600,
    height: 1.3,
    color: AppColors.primary,
  );

  // ADDED HERE: headlineSm style for profile/headers
  static final TextStyle headlineSm = GoogleFonts.epilogue(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    height: 1.3,
    color: AppColors.onSurface,
  );

  // --- Manrope Font Family Styles (Body Copy & Metadata) ---
  static final TextStyle bodyLg = GoogleFonts.manrope(
    fontSize: 18,
    fontWeight: FontWeight.w400,
    height: 1.6,
    color: AppColors.onSurface,
  );

  static final TextStyle bodyMd = GoogleFonts.manrope(
    fontSize: 16,
    fontWeight: FontWeight.w400,
    height: 1.6,
    color: AppColors.onSurfaceVariant,
  );

  // ADDED HERE: bodySm style for secondary descriptions
  static final TextStyle bodySm = GoogleFonts.manrope(
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 1.4,
    color: AppColors.onSurfaceVariant,
  );

  static final TextStyle labelMd = GoogleFonts.manrope(
    fontSize: 14,
    fontWeight: FontWeight.w600,
    height: 1.4,
    letterSpacing: 0.7, // Matches tailwind "0.05em"
    color: AppColors.onSurfaceVariant,
  );

  // ADDED HERE: labelLg style for uppercase group headers
  static final TextStyle labelLg = GoogleFonts.manrope(
    fontSize: 12,
    fontWeight: FontWeight.w700,
    height: 1.1,
    letterSpacing: 0.8,
    color: AppColors.primaryContainer,
  );
}