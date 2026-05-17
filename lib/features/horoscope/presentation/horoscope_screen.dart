import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../constants/app_colors.dart';
import '../../horoscope/providers/horoscope_providers.dart';

class HoroscopeView extends ConsumerWidget {
  const HoroscopeView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(horoscopeProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.only(left: 16.0, right: 16.0, top: 24.0, bottom: 120.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Daily Horoscope',
            style: TextStyle(fontFamily: 'Epilogue', fontSize: 28, fontWeight: FontWeight.bold, color: AppColors.onSurface),
          ),
          const SizedBox(height: 8),
          const Text(
            'Align your day with cosmic wisdom. Predictions based on the Vedic Lunar Calendar.',
            style: TextStyle(fontSize: 16, color: AppColors.onSurfaceVariant, height: 1.4),
          ),
          const SizedBox(height: 20),

          // Duration Switch Tabs
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(color: Colors.black.withOpacity(0.03), borderRadius: BorderRadius.circular(12)),
                child: Row(
                  children: [
                    _buildTextTabButton(ref, state.activeDuration, 'Daily'),
                    _buildTextTabButton(ref, state.activeDuration, 'Weekly'),
                    _buildTextTabButton(ref, state.activeDuration, 'Monthly'),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Horizontal Zodiac Scroller
          SizedBox(
            height: 105,
            child: ListView(
              scrollDirection: Axis.horizontal,
              clipBehavior: Clip.none,
              children: [
                _buildZodiacCard(ref, state.selectedZodiac, LucideIcons.sun, 'Aries'),
                const SizedBox(width: 16),
                _buildZodiacCard(ref, state.selectedZodiac, LucideIcons.trees, 'Taurus'),
                const SizedBox(width: 16),
                _buildZodiacCard(ref, state.selectedZodiac, LucideIcons.users, 'Gemini'),
                const SizedBox(width: 16),
                _buildZodiacCard(ref, state.selectedZodiac, LucideIcons.waves, 'Cancer'),
                const SizedBox(width: 16),
                _buildZodiacCard(ref, state.selectedZodiac, LucideIcons.star, 'Leo'),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Detailed Prediction Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppColors.outlineVariant.withOpacity(0.3)),
              boxShadow: [BoxShadow(color: AppColors.primary.withOpacity(0.08), blurRadius: 20, offset: const Offset(0, 4))],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(color: AppColors.primaryContainer.withOpacity(0.15), shape: BoxShape.circle),
                      child: const Icon(LucideIcons.sun, color: AppColors.primaryContainer, size: 28),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${state.selectedZodiac} Prediction', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.onSurface)),
                          const SizedBox(height: 2),
                          const Text('Oct 24, 2023 • Shardiya Navratri', style: TextStyle(fontSize: 12, color: AppColors.onSurfaceVariant)),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(color: AppColors.primaryContainer.withOpacity(0.15), borderRadius: BorderRadius.circular(100)),
                      child: const Text('95% Auspicious', style: TextStyle(color: AppColors.onPrimaryContainer, fontSize: 11, fontWeight: FontWeight.bold)),
                    )
                  ],
                ),
                const SizedBox(height: 20),
                Text(
                  '"Today marks a period of significant growth for ${state.selectedZodiac}. The Moon\'s alignment suggests that your natural leadership will be recognized in unexpected circles."',
                  style: const TextStyle(fontSize: 18, fontStyle: FontStyle.italic, color: AppColors.onSurface, height: 1.5),
                ),
                const SizedBox(height: 20),
                _buildCategoryPredictionRow(LucideIcons.heart, 'Love', 'A harmonious day for relationships. Communicate openly with your partner about future goals.'),
                const SizedBox(height: 12),
                _buildCategoryPredictionRow(LucideIcons.briefcase, 'Career', 'Strategic moves will pay off. Avoid impulsive financial decisions during the Rahu Kaal period.'),
                const SizedBox(height: 12),
                _buildCategoryPredictionRow(LucideIcons.activity, 'Health', 'Vitality is high. Perfect time to start a new yoga routine or meditation practice.'),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Planetary Transits Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: Colors.black.withOpacity(0.03), borderRadius: BorderRadius.circular(24)),
            child: Stack(
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Planetary Transits', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.onSurface)),
                    const SizedBox(height: 8),
                    const FractionallySizedBox(
                      widthFactor: 0.7,
                      child: Text(
                        'Sun enters Libra today, shifting the collective focus toward balance, justice, and diplomatic partnerships.',
                        style: TextStyle(fontSize: 14, color: AppColors.onSurfaceVariant, height: 1.4),
                      ),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: state.isChartLoading
                          ? null
                          : () => ref.read(horoscopeProvider.notifier).handleViewFullChartPressed(),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                      ),
                      icon: state.isChartLoading 
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                          : const Text('View Full Chart', style: TextStyle(fontWeight: FontWeight.bold)),
                      label: state.isChartLoading ? const SizedBox.shrink() : const Icon(LucideIcons.arrowRight, size: 16),
                    )
                  ],
                ),
                Positioned(
                  right: -10,
                  top: 0,
                  bottom: 0,
                  child: Opacity(
                    opacity: 0.15,
                    child: Icon(LucideIcons.orbit, size: 100, color: AppColors.primary.withOpacity(0.5)),
                  ),
                )
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextTabButton(WidgetRef ref, String activeDuration, String targetText) {
    final bool isSelected = activeDuration == targetText;
    return GestureDetector(
      onTap: () => ref.read(horoscopeProvider.notifier).handleDurationChange(targetText),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
        decoration: BoxDecoration(color: isSelected ? AppColors.primary : Colors.transparent, borderRadius: BorderRadius.circular(8)),
        child: Text(
          targetText,
          style: TextStyle(color: isSelected ? Colors.white : AppColors.onSurfaceVariant, fontWeight: FontWeight.bold, fontSize: 14),
        ),
      ),
    );
  }

  Widget _buildZodiacCard(WidgetRef ref, String activeZodiac, IconData icon, String targetZodiac) {
    final bool isSelected = activeZodiac == targetZodiac;
    return InkWell(
      onTap: () => ref.read(horoscopeProvider.notifier).handleZodiacSelection(targetZodiac),
      borderRadius: BorderRadius.circular(16),
      child: Opacity(
        opacity: isSelected ? 1.0 : 0.5,
        child: Container(
          width: 100,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border(bottom: BorderSide(color: isSelected ? AppColors.primary : Colors.transparent, width: 4)),
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(isSelected ? 0.1 : 0.03), blurRadius: 10, offset: const Offset(0, 2))],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: isSelected ? AppColors.primary : AppColors.onSurfaceVariant, size: 32),
              const SizedBox(height: 8),
              Text(targetZodiac, style: TextStyle(fontSize: 14, fontWeight: isSelected ? FontWeight.bold : FontWeight.w600, color: AppColors.onSurface)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCategoryPredictionRow(IconData icon, String title, String body) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.black.withOpacity(0.015), borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: AppColors.primary, size: 18),
              const SizedBox(width: 8),
              Text(title.toUpperCase(), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5, color: AppColors.primary)),
            ],
          ),
          const SizedBox(height: 6),
          Text(body, style: TextStyle(fontSize: 14, color: AppColors.onSurfaceVariant, height: 1.4)),
        ],
      ),
    );
  }
}