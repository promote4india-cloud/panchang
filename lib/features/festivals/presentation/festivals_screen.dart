import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../../../constants/app_colors.dart';
import '../../../constants/app_themes.dart';
import '../../panchang/models/panchang_models.dart';
import '../providers/festivals_providers.dart';

class FestivalsView extends ConsumerWidget {
  const FestivalsView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Dynamic breakpoint tracking
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth > 768;
    final isCompactHeader = screenWidth < 560;
    final c = AppColorsOf(context);

    final calendar = ref.watch(festivalsCalendarProvider);

    return calendar.when(
      data: (vm) => SingleChildScrollView(
        padding: EdgeInsets.only(
          left: 16.0,
          right: 16.0,
          top: 24.0,
          bottom: MediaQuery.of(context).viewPadding.bottom + 20,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // --- Hero Month Header Section ---
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  vm.masaRangeLabel,
                  maxLines: 2,
                  softWrap: true,
                  style: AppThemes.labelMd.copyWith(
                    color: c.primaryContainer,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.5,
                  ),
                ),
                const SizedBox(height: 12),
                Center(
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: c.subtleBg,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: c.border),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildSelectorStepper(
                          context,
                          value: _monthName(vm.month),
                          onPrevious: () {
                            ref
                                .read(festivalMonthProvider.notifier)
                                .setMonth(DateTime(vm.year, vm.month - 1, 1));
                          },
                          onNext: () {
                            ref
                                .read(festivalMonthProvider.notifier)
                                .setMonth(DateTime(vm.year, vm.month + 1, 1));
                          },
                        ),
                        const SizedBox(width: 8),
                        _buildSelectorStepper(
                          context,
                          value: vm.year.toString(),
                          onPrevious: () {
                            ref
                                .read(festivalMonthProvider.notifier)
                                .setMonth(DateTime(vm.year - 1, vm.month, 1));
                          },
                          onNext: () {
                            ref
                                .read(festivalMonthProvider.notifier)
                                .setMonth(DateTime(vm.year + 1, vm.month, 1));
                          },
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // --- Calendar Layout Section Splits ---
            if (isDesktop)
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    flex: 7,
                    child: _buildGridCalendarBlock(context, screenWidth, vm),
                  ),
                  const SizedBox(width: 24),
                  Expanded(
                    flex: 5,
                    child: _buildSideEventsBarBlock(
                      context,
                      _featuredEvents(vm.events),
                    ),
                  ),
                ],
              )
            else
              Column(
                children: [
                  _buildGridCalendarBlock(context, screenWidth, vm),
                  const SizedBox(height: 20),
                  _buildSideEventsBarBlock(
                    context,
                    _featuredEvents(vm.events),
                  ),
                ],
              ),
            const SizedBox(height: 24),

            // --- Fixed: Mobile Responsive List Alternative View to replace table ---
            Text(
              'Full Calendar View',
              style: AppThemes.headlineMd.copyWith(
                color: c.onSurface,
                fontSize: 20,
              ),
            ),
            const SizedBox(height: 12),
            if (vm.events.isEmpty)
              Text(
                'No festivals listed for this month.',
                style: AppThemes.bodyMd.copyWith(
                  color: c.onSurfaceVariant,
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: vm.events.length,
                itemBuilder: (context, index) {
                  final event = vm.events[index];
                  return _buildResponsiveCalendarRow(
                    context,
                    _formatEventDate(event.date),
                    event.weekday,
                    event.name,
                    _eventTypeLabel(event.type),
                    c.primaryContainer,
                  );
                },
              ),
          ],
        ),
      ),
      loading: () => Center(
        child: CircularProgressIndicator(color: c.primary),
      ),
      error: (error, stackTrace) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Unable to load festivals.',
              style: AppThemes.bodyMd.copyWith(
                color: c.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () => ref.refresh(festivalsCalendarProvider),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  // =========================================================================
  // SUB-LAYOUT MODULAR BUILDERS
  // =========================================================================

  Widget _buildSelectorStepper(
    BuildContext context, {
    required String value,
    required VoidCallback onPrevious,
    required VoidCallback onNext,
  }) {
    final c = AppColorsOf(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(
            color: c.card.withOpacity(0.65),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: c.border),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                icon: Icon(LucideIcons.chevronLeft, size: 16, color: c.onSurface),
                onPressed: onPrevious,
                constraints: const BoxConstraints(),
                padding: const EdgeInsets.all(4),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8.0),
                child: Text(
                  value,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    fontFamily: 'Manrope',
                    color: c.onSurface,
                  ),
                ),
              ),
              IconButton(
                icon: Icon(LucideIcons.chevronRight, size: 16, color: c.onSurface),
                onPressed: onNext,
                constraints: const BoxConstraints(),
                padding: const EdgeInsets.all(4),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildGridCalendarBlock(
    BuildContext context,
    double screenWidth,
    FestivalsCalendarVm vm,
  ) {
    final c = AppColorsOf(context);
    final startWeekday = DateTime(vm.year, vm.month, 1).weekday;
    final leadingEmpty = startWeekday % 7;
    final totalDays = vm.days.length;
    final totalCells = leadingEmpty + totalDays;
    final trailingEmpty = (7 - (totalCells % 7)) % 7;

    final cells = <Widget>[];
    for (var i = 0; i < leadingEmpty; i++) {
      cells.add(_buildEmptyDayCell(context));
    }
    for (final day in vm.days) {
      cells.add(
        _buildDayCell(
          context,
          day.day.toString(),
          date: DateTime(vm.year, vm.month, day.day),
          events: day.events,
        ),
      );
    }
    for (var i = 0; i < trailingEmpty; i++) {
      cells.add(_buildEmptyDayCell(context));
    }

    return Container(
      decoration: BoxDecoration(
        color: c.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: c.border),
        boxShadow: [
          BoxShadow(
            color: c.primary.withOpacity(0.04),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          // Seven Days Column Header Titles Label row
          Container(
            padding: const EdgeInsets.symmetric(vertical: 10),
            color: c.subtleBg,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                for (final day in ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'])
                  Expanded(
                    child: Text(
                      day,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: c.onSurfaceVariant,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          // Grid Days Matrix
          GridView.count(
            crossAxisCount: 7,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            childAspectRatio: screenWidth > 400
                ? 0.75
                : 0.65, // Dynamically scales spacing based on device width
            children: cells,
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyDayCell(BuildContext context) {
    final c = AppColorsOf(context);
    return Container(
      decoration: BoxDecoration(
        color: c.isDark ? Colors.white.withOpacity(0.01) : Colors.black.withOpacity(0.01),
        border: Border.all(color: c.outlineVariant.withOpacity(0.1)),
      ),
    );
  }

  Widget _buildDayCell(
    BuildContext context,
    String day, {
    required DateTime date,
    List<FestivalCalendarEventDto> events = const [],
  }) {
    final c = AppColorsOf(context);
    final tag = _buildEventTag(events);
    final isHighlighted = events.isNotEmpty;
    return InkWell(
      onTap: events.isEmpty
          ? null
          : () => _showDayEventsDialog(context, date, events),
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.all(2),
        decoration: BoxDecoration(
          color: isHighlighted
              ? c.primaryContainer.withOpacity(0.05)
              : Colors.transparent,
          border: Border.all(color: c.outlineVariant.withOpacity(0.1)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              day,
              style: TextStyle(
                fontWeight: isHighlighted ? FontWeight.bold : FontWeight.normal,
                color: isHighlighted
                    ? c.primaryContainer
                    : c.onSurface,
                fontSize: 12,
              ),
            ),
            if (tag != null)
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Container(
                      width: 4,
                      height: 4,
                      decoration: BoxDecoration(
                        color: c.primaryContainer,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(height: 2),
                    WidthSizedBoxMax(
                      child: Text(
                        tag,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 7.5,
                          fontWeight: FontWeight.bold,
                          color: c.primaryContainer,
                        ),
                      ),
                    ),
                  ],
                ),
              )
            else
              const SizedBox.shrink(),
          ],
        ),
      ),
    );
  }

  void _showDayEventsDialog(
    BuildContext context,
    DateTime date,
    List<FestivalCalendarEventDto> events,
  ) {
    final c = AppColorsOf(context);
    showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(' ${_formatFullDate(date)}'),
          content: SizedBox(
            width: double.maxFinite,
            child: ListView.separated(
              shrinkWrap: true,
              itemCount: events.length,
              separatorBuilder: (_, __) => const Divider(height: 12),
              itemBuilder: (context, index) {
                final event = events[index];
                return Text(
                  event.name,
                  style: AppThemes.bodyMd.copyWith(color: c.onSurface),
                );
              },
            ),
          ),
          actions: [
            TextButton(
              style: TextButton.styleFrom(
                foregroundColor: c.primaryContainer,
              ),
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  String? _buildEventTag(List<FestivalCalendarEventDto> events) {
    if (events.isEmpty) return null;
    if (events.length == 1) return events.first.name;
    return '${events.first.name} +${events.length - 1}';
  }

  String _formatEventDate(DateTime date) {
    final day = date.day.toString().padLeft(2, '0');
    return '${_monthShort(date.month)} $day, ${_weekdayShort(date.weekday)}';
  }

  String _formatFeaturedDate(DateTime date) {
    return '${_monthName(date.month)} ${date.day}';
  }

  String _eventTypeLabel(String? type) {
    if (type == null || type.trim().isEmpty) return 'FESTIVAL';
    return type.trim().toUpperCase();
  }

  String _monthShort(int month) {
    const months = [
      'JAN',
      'FEB',
      'MAR',
      'APR',
      'MAY',
      'JUN',
      'JUL',
      'AUG',
      'SEP',
      'OCT',
      'NOV',
      'DEC',
    ];
    return months[(month - 1).clamp(0, 11)];
  }

  String _monthName(int month) {
    const months = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    return months[(month - 1).clamp(0, 11)];
  }

  String _weekdayShort(int weekday) {
    const weekdays = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
    return weekdays[(weekday - 1).clamp(0, 6)];
  }

  String _formatFullDate(DateTime date) {
    return '${_monthName(date.month)} ${date.day}, ${date.year}';
  }

  List<FestivalCalendarEventVm> _featuredEvents(
    List<FestivalCalendarEventVm> events,
  ) {
    if (events.isEmpty) return [];
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, today.day);
    final end = start.add(const Duration(days: 6));
    final filtered = events.where((event) {
      final date = DateTime(event.date.year, event.date.month, event.date.day);
      return !date.isBefore(start) && !date.isAfter(end);
    }).toList();
    filtered.sort((a, b) => a.date.compareTo(b.date));
    return filtered;
  }

  Widget _buildSideEventsBarBlock(
    BuildContext context,
    List<FestivalCalendarEventVm> featuredEvents,
  ) {
    final c = AppColorsOf(context);
    return Column(
      children: [
        if (featuredEvents.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: c.card,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: c.border),
              boxShadow: [
                BoxShadow(
                  color: c.primary.withOpacity(0.04),
                  blurRadius: 20,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      LucideIcons.star,
                      color: c.primaryContainer,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Featured Festivals',
                      style: AppThemes.headlineMd.copyWith(
                        color: c.onSurface,
                        fontSize: 18,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                for (var i = 0; i < featuredEvents.length; i++) ...[
                  _buildFeaturedFestivalItem(
                    context,
                    _formatFeaturedDate(featuredEvents[i].date),
                    _eventTypeLabel(featuredEvents[i].type),
                    featuredEvents[i].name,
                  ),
                  if (i != featuredEvents.length - 1)
                    const SizedBox(height: 12),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
      ],
    );
  }

  Widget _buildFeaturedFestivalItem(
    BuildContext context,
    String date,
    String statusLabel,
    String title, [
    String description = '',
  ]) {
    final c = AppColorsOf(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: c.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border(
          left: BorderSide(color: c.primaryContainer, width: 4),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                date,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: c.primaryContainer,
                  fontFamily: 'Manrope',
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: c.primaryContainer.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(100),
                ),
                child: Text(
                  statusLabel.toUpperCase(),
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                    color: c.primaryContainer,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            title,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: c.onSurface,
              fontFamily: 'Manrope',
            ),
          ),
          if (description.trim().isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              description,
              style: TextStyle(
                fontSize: 12,
                color: c.onSurfaceVariant,
                height: 1.4,
                fontFamily: 'Manrope',
              ),
            ),
          ],
        ],
      ),
    );
  }

  // Custom adaptive component built to look clean on compact viewport sizes
  Widget _buildResponsiveCalendarRow(
    BuildContext context,
    String date,
    String paksha,
    String festival,
    String urgency,
    Color highlightColor,
  ) {
    final c = AppColorsOf(context);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: c.card,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: c.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            flex: 3,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  date,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                    color: c.onSurface,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  paksha,
                  style: TextStyle(
                    color: c.onSurfaceVariant,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            flex: 4,
            child: Text(
              festival,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 13,
                color: c.onSurface,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: highlightColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(100),
            ),
            child: Text(
              urgency,
              style: TextStyle(
                color: highlightColor,
                fontSize: 9,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Micro-helper container used to enforce hard truncation bounds
class WidthSizedBoxMax extends StatelessWidget {
  final Widget child;
  const WidthSizedBoxMax({required this.child, super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(width: double.infinity, child: child);
  }
}
