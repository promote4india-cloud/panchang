import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../constants/app_colors.dart';
import '../../../constants/app_themes.dart';

class PanchangDashboardView extends StatelessWidget {
  const PanchangDashboardView({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      // Padding tailored to clear the bottom navigation dock area
      padding: const EdgeInsets.only(left: 16.0, right: 16.0, top: 24.0, bottom: 120.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // --- Hero Date Header ---
          Text(
            '16 May 2026 | Tuesday',
            textAlign: TextAlign.center,
            style: AppThemes.headlineLgMobile,
          ),
          const SizedBox(height: 4),
          Text(
            'Vaishakha Shukla Tritiya',
            textAlign: TextAlign.center,
            style: AppThemes.headlineMd.copyWith(color: AppColors.primary),
          ),
          const SizedBox(height: 24),

          // --- Festival Today Card (Highlight) ---
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.primaryContainer.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.primaryContainer.withOpacity(0.3)),
              boxShadow: [
                BoxShadow(
                  color: AppColors.primaryContainer.withOpacity(0.15),
                  blurRadius: 20,
                  offset: const Offset(0, 4),
                )
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: const BoxDecoration(
                    color: AppColors.primaryContainer,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(LucideIcons.partyPopper, color: Colors.white, size: 24),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Festival Today', style: AppThemes.labelMd),
                      Text(
                        'Parshurama Jayanti',
                        style: AppThemes.headlineMd.copyWith(color: AppColors.onPrimaryContainer, fontSize: 20),
                      ),
                    ],
                  ),
                ),
                const Icon(LucideIcons.chevronRight, color: AppColors.primaryContainer),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // --- Bento Grid for Astro Data ---
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Left Box: Tithi & Nakshatra
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: _bentoBoxDecoration(),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(LucideIcons.moon, color: AppColors.primaryContainer, size: 18),
                          const SizedBox(width: 8),
                          Text('Tithi', style: AppThemes.labelMd),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text('Shukla Tritiya', style: AppThemes.headlineMd.copyWith(color: AppColors.onSurface, fontSize: 18)),
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8.0),
                        child: Divider(color: AppColors.outlineVariant.withOpacity(0.5), height: 1),
                      ),
                      Row(
                        children: [
                          const Icon(LucideIcons.sparkles, color: AppColors.primaryContainer, size: 18),
                          const SizedBox(width: 8),
                          Text('Nakshatra', style: AppThemes.labelMd),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text('Rohini', style: AppThemes.headlineMd.copyWith(color: AppColors.onSurface, fontSize: 18)),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 16),
              // Right Box: Sunrise & Sunset
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: _bentoBoxDecoration(),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Sunrise', style: AppThemes.labelMd),
                              Text('5:45 AM', style: AppThemes.headlineMd.copyWith(color: AppColors.onSurface, fontSize: 18)),
                            ],
                          ),
                          const Icon(LucideIcons.sun, color: AppColors.primaryContainer),
                        ],
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 10.0),
                        child: Divider(color: AppColors.outlineVariant.withOpacity(0.5), height: 1),
                      ),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Sunset', style: AppThemes.labelMd),
                              Text('6:45 PM', style: AppThemes.headlineMd.copyWith(color: AppColors.onSurface, fontSize: 18)),
                            ],
                          ),
                          const Icon(LucideIcons.sunset, color: AppColors.onSurfaceVariant),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // --- Muhurat Section ---
          Container(
            padding: const EdgeInsets.all(12),
            decoration: _bentoBoxDecoration(),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(LucideIcons.clock, color: AppColors.primaryContainer),
                        const SizedBox(width: 8),
                        Text('Muhurat Timings', style: AppThemes.headlineMd.copyWith(color: AppColors.onSurface, fontSize: 20)),
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppColors.primaryContainer,
                        borderRadius: BorderRadius.circular(100),
                      ),
                      child: const Text(
                        'AUSPICIOUS',
                        style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1),
                      ),
                    )
                  ],
                ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.02),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Shubh Muhurat', style: AppThemes.labelMd),
                          Text('11:50 AM - 12:45 PM', style: AppThemes.bodyLg.copyWith(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const Icon(LucideIcons.checkCircle, color: AppColors.primaryContainer),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.errorContainerBg.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.error.withOpacity(0.1)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Rahu Kaal (Avoid)', style: AppThemes.labelMd.copyWith(color: AppColors.error)),
                          Text('2:00 PM - 3:30 PM', style: AppThemes.bodyLg.copyWith(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const Icon(LucideIcons.alertTriangle, color: AppColors.error),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // --- RESTORED: Rashifal Preview Block ---
          Container(
            padding: const EdgeInsets.all(12),
            decoration: _bentoBoxDecoration(),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Daily Rashifal', style: AppThemes.headlineMd.copyWith(color: AppColors.onSurface, fontSize: 20)),
                    TextButton(
                      onPressed: () {},
                      style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: Size.zero),
                      child: Row(
                        children: [
                          Text('View All ', style: AppThemes.labelMd.copyWith(color: AppColors.primaryContainer, fontWeight: FontWeight.bold)),
                          const Icon(LucideIcons.chevronRight, size: 16, color: AppColors.primaryContainer),
                        ],
                      ),
                    )
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Column(
                      children: [
                        Container(
                          width: 64,
                          height: 64,
                          decoration: BoxDecoration(
                            color: AppColors.primaryContainer.withOpacity(0.1),
                            shape: BoxShape.circle,
                            border: Border.all(color: AppColors.primaryContainer.withOpacity(0.3), width: 2),
                          ),
                          child: const Icon(LucideIcons.star, color: AppColors.primaryContainer),
                        ),
                        const SizedBox(height: 4),
                        Text('Aries', style: AppThemes.labelMd.copyWith(color: AppColors.onSurface, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.black.withOpacity(0.02),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '"Your celestial alignment suggests a day of immense financial growth. New opportunities await in the workspace, focus on collaborative efforts for maximum success..."',
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: AppThemes.bodyMd.copyWith(fontStyle: FontStyle.italic),
                        ),
                      ),
                    )
                  ],
                )
              ],
            ),
          ),
          const SizedBox(height: 16),

          // --- RESTORED: Upcoming Events Block ---
          Container(
            padding: const EdgeInsets.all(12),
            decoration: _bentoBoxDecoration(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Upcoming Events', style: AppThemes.headlineMd.copyWith(color: AppColors.onSurface, fontSize: 20)),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    border: Border.all(color: AppColors.outlineVariant),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: AppColors.primaryContainer,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Column(
                          children: [
                            Text('MAY', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                            Text('19', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold, height: 1.1)),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Mohini Ekadashi', style: AppThemes.labelMd.copyWith(color: AppColors.onSurface, fontWeight: FontWeight.bold)),
                            Text('Vrat and Puja Vidhi', style: AppThemes.bodyMd.copyWith(fontSize: 12)),
                          ],
                        ),
                      ),
                      ElevatedButton(
                        onPressed: () {},
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primaryContainer,
                          foregroundColor: Colors.white,
                          elevation: 2,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        child: const Text('Set Reminder', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                      ),
                    ],
                  ),
                )
              ],
            ),
          ),
          const SizedBox(height: 16),

          // --- Featured Artwork Section ---
          Container(
            height: 224,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: AppColors.primaryContainer.withOpacity(0.15),
                  blurRadius: 20,
                  offset: const Offset(0, 4),
                )
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Stack(
                children: [
                  Positioned.fill(
                    child: Image.network(
                      'https://lh3.googleusercontent.com/aida-public/AB6AXuDjJ4jq73RyQxCpoOLyPSIWgvYSa2sBslby8yViZnO8oFFjP1cbAVbVp7hXqR7r7W4wyxQy-0gqDa5ldnBZOXidQOXjazU3fcPPUqv1nVCi6zyKMaBZzuOIq5mGej9DN0gzB55mmW1t3bdpNgSg7oKEpNgPi-aOBw2aRiX9Xiw3aiclL8v0MGvZnxYzO4ASwYtl6sezwH0b4gDued7HHE6jezRnftO4uFJR4adnv9uJd-uiPMigzQWGp1nc9QXflvHYd6glFP9YntY',
                      fit: BoxFit.cover,
                    ),
                  ),
                  Positioned.fill(
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Colors.transparent,
                            AppColors.primaryContainer.withOpacity(0.8),
                          ],
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    left: 12,
                    bottom: 12,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Astrological Insights', style: AppThemes.headlineLgMobile.copyWith(color: Colors.white, fontSize: 20)),
                        const Text('Connect with the cosmos today.', style: TextStyle(color: Colors.white70, fontSize: 14)),
                      ],
                    ),
                  )
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  BoxDecoration _bentoBoxDecoration() {
    return BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      boxShadow: [
        BoxShadow(
          color: AppColors.primary.withOpacity(0.06),
          blurRadius: 20,
          offset: const Offset(0, 4),
        )
      ],
    );
  }
}