import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:panchang_app/l10n/app_localizations.dart';
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
    final c = AppColorsOf(context);

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
      padding: EdgeInsets.only(
        left: 16.0,
        right: 16.0,
        top: 24.0,
        bottom: MediaQuery.of(context).viewPadding.bottom + 20,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            AppLocalizations.of(context)!.horoscopeTitle(state.activeDuration),
            style: TextStyle(fontFamily: 'Epilogue', fontSize: 28, fontWeight: FontWeight.bold, color: c.onSurface),
          ),
          const SizedBox(height: 8),
          Text(
            AppLocalizations.of(context)!.horoscopeSubtitle,
            style: TextStyle(fontSize: 16, color: c.onSurfaceVariant, height: 1.4),
          ),
          const SizedBox(height: 20),

          // Duration Switch Tabs
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(color: c.subtleBg, borderRadius: BorderRadius.circular(12)),
                child: Row(
                  children: [
                    _buildTextTabButton(ref, c, state.activePeriod, AppLocalizations.of(context)!.durationDaily, 'daily'),
                    _buildTextTabButton(ref, c, state.activePeriod, AppLocalizations.of(context)!.durationWeekly, 'weekly'),
                    _buildTextTabButton(ref, c, state.activePeriod, AppLocalizations.of(context)!.durationMonthly, 'monthly'),
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
                  _buildZodiacCard(ref, c, state.selectedZodiac, item.icon, item.label),
                  const SizedBox(width: 16),
                ]),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Detailed Prediction Card
          _buildPredictionCard(context, state, forecast),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildTextTabButton(WidgetRef ref, AppColorsOf c, String activePeriod, String displayLabel, String periodKey) {
    final bool isSelected = activePeriod == periodKey;
    return GestureDetector(
      onTap: () => ref.read(horoscopeProvider.notifier).handleDurationChange(displayLabel, periodKey),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
        decoration: BoxDecoration(color: isSelected ? c.primary : Colors.transparent, borderRadius: BorderRadius.circular(8)),
        child: Text(
          displayLabel,
          style: TextStyle(color: isSelected ? Colors.white : c.onSurfaceVariant, fontWeight: FontWeight.bold, fontSize: 14),
        ),
      ),
    );
  }

  Widget _buildZodiacCard(WidgetRef ref, AppColorsOf c, String activeZodiac, IconData icon, String targetZodiac) {
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
            color: c.card,
            borderRadius: BorderRadius.circular(16),
            border: Border(bottom: BorderSide(color: isSelected ? c.primary : Colors.transparent, width: 4)),
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
                  color: isSelected ? c.primary : c.onSurfaceVariant,
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
                      color: c.onSurface,
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
  BuildContext context,
  HoroscopeState state,
  AsyncValue<HoroscopePredictionDto> forecast,
) {
  final c = AppColorsOf(context);
  return Container(
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: c.card,
      borderRadius: BorderRadius.circular(24),
      border: Border.all(color: c.border),
      boxShadow: [
        BoxShadow(
          color: c.primary.withOpacity(0.08),
          blurRadius: 20,
          offset: const Offset(0, 4),
        ),
      ],
    ),
    child: forecast.when(
      loading: () => Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 24),
          child: CircularProgressIndicator(color: c.primary),
        ),
      ),
      error: (error, _) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '${state.selectedZodiac} Prediction',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: c.onSurface,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            error.toString(),
            style: TextStyle(fontSize: 14, color: c.error),
          ),
        ],
      ),
      data: (data) {
        final dateLabel = data.dateLabel ?? '';
        final prediction = data.prediction?.trim().isNotEmpty == true
            ? data.prediction!.trim()
            : AppLocalizations.of(context)!.noHoroscopeAvailable;
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
                    color: c.primaryContainer.withOpacity(0.15),
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      zodiacSymbolFor(state.selectedZodiac),
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        color: c.primaryContainer,
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
                        AppLocalizations.of(context)!.predictionTitle(state.selectedZodiac),
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: c.onSurface,
                        ),
                      ),
                      if (dateLabel.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          dateLabel,
                          style: TextStyle(
                            fontSize: 12,
                            color: c.onSurfaceVariant,
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
                      color: c.primaryContainer.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(100),
                    ),
                    child: Text(
                      ratingLabel,
                      style: TextStyle(
                        color: c.onPrimaryContainer,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 20),
            _ExpandablePredictionText(
              key: ValueKey(
                '${state.selectedZodiac}-${state.activeDuration}-$dateLabel',
              ),
              text: '"$prediction"',
            ),
            if (showRatings) ...[
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: _buildRatingChips(context, data.ratings),
              ),
            ],
            if (showCategories) ...[
              const SizedBox(height: 20),
              ..._buildCategoryRows(context, data.categories),
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

Widget _buildRatingChip(BuildContext context, String label, double rating) {
  final c = AppColorsOf(context);
  final display = rating.toStringAsFixed(rating % 1 == 0 ? 0 : 1);
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    decoration: BoxDecoration(
      color: c.primaryContainer.withOpacity(0.12),
      borderRadius: BorderRadius.circular(999),
    ),
    child: Text(
      '$label $display/5',
      style: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: c.onPrimaryContainer,
      ),
    ),
  );
}

List<Widget> _buildRatingChips(BuildContext context, Map<String, dynamic>? ratings) {
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
            context,
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

List<Widget> _buildCategoryRows(BuildContext context, Map<String, dynamic>? categories) {
  if (categories == null) return const [];
  final rows = <Widget>[];
  void addRow(IconData icon, String label, String key) {
    rows.add(_CategoryPredictionCard(
      icon: icon,
      title: label,
      body: _categoryText(categories, key),
    ));
    rows.add(const SizedBox(height: 12));
  }

  addRow(LucideIcons.heart, AppLocalizations.of(context)!.categoryLove, 'love');
  addRow(LucideIcons.briefcase, AppLocalizations.of(context)!.categoryCareer, 'career');
  addRow(LucideIcons.piggyBank, AppLocalizations.of(context)!.categoryFinance, 'finance');
  addRow(LucideIcons.activity, AppLocalizations.of(context)!.categoryHealth, 'health');
  addRow(LucideIcons.users, AppLocalizations.of(context)!.categoryFamily, 'family');

  if (rows.isNotEmpty) {
    rows.removeLast();
  }
  return rows;
}

class _CategoryPredictionCard extends StatefulWidget {
  final IconData icon;
  final String title;
  final String body;

  const _CategoryPredictionCard({
    required this.icon,
    required this.title,
    required this.body,
  });

  @override
  State<_CategoryPredictionCard> createState() => _CategoryPredictionCardState();
}

class _CategoryPredictionCardState extends State<_CategoryPredictionCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final c = AppColorsOf(context);
    return InkWell(
      onTap: () => setState(() => _expanded = !_expanded),
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: c.subtleBg,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(widget.icon, color: c.primary, size: 18),
                const SizedBox(width: 8),
                Text(
                  widget.title.toUpperCase(),
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                    color: c.primary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              widget.body,
              maxLines: _expanded ? null : 5,
              overflow: _expanded ? TextOverflow.visible : TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 14,
                color: c.onSurfaceVariant,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ExpandablePredictionText extends StatefulWidget {
  final String text;

  const _ExpandablePredictionText({
    super.key,
    required this.text,
  });

  @override
  State<_ExpandablePredictionText> createState() => _ExpandablePredictionTextState();
}

class _ExpandablePredictionTextState extends State<_ExpandablePredictionText> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final c = AppColorsOf(context);
    return InkWell(
      onTap: () => setState(() => _expanded = !_expanded),
      borderRadius: BorderRadius.circular(12),
      child: Text(
        widget.text,
        maxLines: _expanded ? null : 5,
        overflow: _expanded ? TextOverflow.visible : TextOverflow.ellipsis,
        style: TextStyle(
          fontSize: 18,
          fontStyle: FontStyle.italic,
          color: c.onSurface,
          height: 1.5,
        ),
      ),
    );
  }
}