import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../constants/app_colors.dart';
import '../../../assset/zodiac_icons.dart';
import '../../horoscope/providers/horoscope_providers.dart';
import '../models/horoscope_models.dart';

class HoroscopeView extends ConsumerStatefulWidget {
  const HoroscopeView({super.key});

  @override
  ConsumerState<HoroscopeView> createState() => _HoroscopeViewState();
}

class _HoroscopeViewState extends ConsumerState<HoroscopeView> {
  static const double _zodiacCardWidth = 100;
  static const double _zodiacCardGap = 16;
  final ScrollController _zodiacController = ScrollController();
  bool _didSetInitialScroll = false;


  @override
  void dispose() {
    _zodiacController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(horoscopeProvider);
    final forecast = ref.watch(horoscopeDetailsProvider);
    if (!_didSetInitialScroll) {
      final index = zodiacIconItems.indexWhere((item) => item.label == state.selectedZodiac);
      if (index >= 0) {
        _didSetInitialScroll = true;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_zodiacController.hasClients) {
            _zodiacController.jumpTo(
              index * (_zodiacCardWidth + _zodiacCardGap),
            );
          }
        });
      }
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.only(left: 16.0, right: 16.0, top: 24.0, bottom: 120.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '${state.activeDuration} Horoscope',
            style: const TextStyle(fontFamily: 'Epilogue', fontSize: 28, fontWeight: FontWeight.bold, color: AppColors.onSurface),
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
            height: 112,
            child: ListView(
              controller: _zodiacController,
              scrollDirection: Axis.horizontal,
              clipBehavior: Clip.none,
              children: [
                ...zodiacIconItems.expand((item) => [
                  _buildZodiacCard(ref, state.selectedZodiac, item.icon, item.label),
                  const SizedBox(width: 16),
                ]),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Detailed Prediction Card
          _buildPredictionCard(state, forecast),
          const SizedBox(height: 24),
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
    final symbol = zodiacSymbolFor(targetZodiac);
    return InkWell(
      onTap: () => ref.read(horoscopeProvider.notifier).handleZodiacSelection(targetZodiac),
      borderRadius: BorderRadius.circular(16),
      child: Opacity(
        opacity: isSelected ? 1.0 : 0.5,
        child: Container(
          width: 100,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border(bottom: BorderSide(color: isSelected ? AppColors.primary : Colors.transparent, width: 4)),
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(isSelected ? 0.1 : 0.03), blurRadius: 10, offset: const Offset(0, 2))],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                symbol.isEmpty ? '?' : symbol,
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: isSelected ? AppColors.primary : AppColors.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 6),
              Flexible(
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    targetZodiac,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                      color: AppColors.onSurface,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

}


Widget _buildPredictionCard(
  HoroscopeState state,
  AsyncValue<HoroscopePredictionDto> forecast,
) {
  return Container(
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(24),
      border: Border.all(color: AppColors.outlineVariant.withOpacity(0.3)),
      boxShadow: [
        BoxShadow(
          color: AppColors.primary.withOpacity(0.08),
          blurRadius: 20,
          offset: const Offset(0, 4),
        ),
      ],
    ),
    child: forecast.when(
      loading: () => const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 24),
          child: CircularProgressIndicator(color: AppColors.primary),
        ),
      ),
      error: (error, _) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '${state.selectedZodiac} Prediction',
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: AppColors.onSurface,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            error.toString(),
            style: const TextStyle(fontSize: 14, color: AppColors.error),
          ),
        ],
      ),
      data: (data) {
        final dateLabel = data.dateLabel ?? '';
        final prediction = data.prediction?.trim().isNotEmpty == true
            ? data.prediction!.trim()
            : 'No horoscope available right now.';
        final duration = state.activeDuration.toLowerCase();
        final showRatings = duration == 'daily';
        final showCategories = duration == 'monthly';
        final ratingLabel = showRatings ? _formatRatingLabel(data.ratings) : '';
        final love = _categoryText(data.categories, 'love');
        final career = _categoryText(data.categories, 'career');
        final health = _categoryText(data.categories, 'health');

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: AppColors.primaryContainer.withOpacity(0.15),
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      zodiacSymbolFor(state.selectedZodiac),
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        color: AppColors.primaryContainer,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${state.selectedZodiac} Prediction',
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: AppColors.onSurface,
                        ),
                      ),
                      if (dateLabel.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          dateLabel,
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (ratingLabel.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.primaryContainer.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(100),
                    ),
                    child: Text(
                      ratingLabel,
                      style: const TextStyle(
                        color: AppColors.onPrimaryContainer,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 20),
            Text(
              '"$prediction"',
              style: const TextStyle(
                fontSize: 18,
                fontStyle: FontStyle.italic,
                color: AppColors.onSurface,
                height: 1.5,
              ),
            ),
            if (showRatings) ...[
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: _buildRatingChips(data.ratings),
              ),
            ],
            if (showCategories) ...[
              const SizedBox(height: 20),
              ..._buildCategoryRows(data.categories),
            ],
          ],
        );
      },
    ),
  );
}

String _categoryText(Map<String, dynamic>? categories, String key) {
  if (categories == null) return 'No details available yet.';
  final value = categories[key];
  if (value is String && value.trim().isNotEmpty) return value.trim();
  return 'No details available yet.';
}

String _formatRatingLabel(Map<String, dynamic>? ratings) {
  if (ratings == null || ratings.isEmpty) return '';
  final values = ratings.values
      .whereType<num>()
      .map((value) => value.toDouble())
      .toList();
  if (values.isEmpty) return '';
  final avg = values.reduce((a, b) => a + b) / values.length;
  final percent = (avg / 5.0 * 100).round();
  return '$percent% Favorable';
}

double? _ratingValue(Map<String, dynamic>? ratings, String key) {
  if (ratings == null) return null;
  final value = ratings[key];
  if (value is num) return value.toDouble();
  return null;
}

Widget _buildRatingChip(String label, double rating) {
  final display = rating.toStringAsFixed(rating % 1 == 0 ? 0 : 1);
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    decoration: BoxDecoration(
      color: AppColors.primaryContainer.withOpacity(0.12),
      borderRadius: BorderRadius.circular(999),
    ),
    child: Text(
      '$label $display/5',
      style: const TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: AppColors.onPrimaryContainer,
      ),
    ),
  );
}

List<Widget> _buildRatingChips(Map<String, dynamic>? ratings) {
  if (ratings == null || ratings.isEmpty) return const [];
  const order = [
    'health',
    'wealth',
    'family',
    'love_matters',
    'occupation',
    'married_life',
  ];
  return order
      .map((key) => MapEntry(key, _ratingValue(ratings, key)))
      .where((entry) => entry.value != null)
      .map((entry) => _buildRatingChip(
            _ratingLabelForKey(entry.key),
            entry.value!,
          ))
      .toList();
}

String _ratingLabelForKey(String key) {
  switch (key) {
    case 'love_matters':
      return 'Love';
    case 'occupation':
      return 'Career';
    case 'married_life':
      return 'Marriage';
    default:
      return key.replaceAll('_', ' ').split(' ').map((word) {
        if (word.isEmpty) return word;
        return word[0].toUpperCase() + word.substring(1);
      }).join(' ');
  }
}

List<Widget> _buildCategoryRows(Map<String, dynamic>? categories) {
  if (categories == null) return const [];
  final rows = <Widget>[];
  void addRow(IconData icon, String label, String key) {
    rows.add(_buildCategoryPredictionRow(
      icon,
      label,
      _categoryText(categories, key),
    ));
    rows.add(const SizedBox(height: 12));
  }

  addRow(LucideIcons.heart, 'Love', 'love');
  addRow(LucideIcons.briefcase, 'Career', 'career');
  addRow(LucideIcons.piggyBank, 'Finance', 'finance');
  addRow(LucideIcons.activity, 'Health', 'health');
  addRow(LucideIcons.users, 'Family', 'family');

  if (rows.isNotEmpty) {
    rows.removeLast();
  }
  return rows;
}

Widget _buildCategoryPredictionRow(IconData icon, String title, String body) {
  return Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: Colors.black.withOpacity(0.015),
      borderRadius: BorderRadius.circular(16),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, color: AppColors.primary, size: 18),
            const SizedBox(width: 8),
            Text(
              title.toUpperCase(),
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.5,
                color: AppColors.primary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          body,
          style: TextStyle(
            fontSize: 14,
            color: AppColors.onSurfaceVariant,
            height: 1.4,
          ),
        ),
      ],
    ),
  );
}