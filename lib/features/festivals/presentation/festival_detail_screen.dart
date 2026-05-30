import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../constants/app_colors.dart';
import '../../../constants/app_themes.dart';
import '../../panchang/models/panchang_models.dart';
import '../../panchang/providers/panchang_providers.dart';
import '../providers/festivals_providers.dart';

class FestivalDetailScreen extends ConsumerStatefulWidget {
  final List<FestivalCalendarEventVm> events;
  final int initialIndex;

  const FestivalDetailScreen({
    super.key,
    required this.events,
    required this.initialIndex,
  });

  @override
  ConsumerState<FestivalDetailScreen> createState() => _FestivalDetailScreenState();
}

class _FestivalDetailScreenState extends ConsumerState<FestivalDetailScreen> {
  late final PageController _controller;
  int _index = 0;
  final Map<String, Future<FestivalDatesResponseDto>> _datesCache = {};
  final Map<String, bool> _expandedSections = {};

  @override
  void initState() {
    super.initState();
    _index = widget.initialIndex.clamp(0, widget.events.length - 1);
    _controller = PageController(initialPage: _index);
    _primeDates(widget.events[_index]);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColorsOf(context);
    final current = widget.events[_index];
    return Scaffold(
      appBar: AppBar(
        backgroundColor: c.surface,
        surfaceTintColor: Colors.transparent,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text(
          _displayName(current),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppThemes.headlineSm.copyWith(color: c.onSurface),
        ),
      ),
      body: PageView.builder(
        controller: _controller,
        itemCount: widget.events.length,
        onPageChanged: (value) {
          setState(() => _index = value);
          _primeDates(widget.events[value]);
        },
        itemBuilder: (context, index) {
          return _buildDetailPage(context, widget.events[index]);
        },
      ),
    );
  }

  Widget _buildDetailPage(BuildContext context, FestivalCalendarEventVm event) {
    final future = _datesFutureForEvent(event);
    return FutureBuilder<FestivalDatesResponseDto>(
      future: future,
      builder: (context, snapshot) {
        final c = AppColorsOf(context);
        final content = event.content;
        final sections = <Widget>[];
        if (_hasText(content?.about)) {
          sections.add(
            _buildSection(
              context,
              'About',
              content?.about ?? '',
              _sectionKey(event, 'about'),
            ),
          );
        }
        if (_hasText(content?.significance)) {
          sections.add(
            _buildSection(
              context,
              'Importance',
              content?.significance ?? '',
              _sectionKey(event, 'importance'),
            ),
          );
        }
        if (_hasText(content?.history)) {
          sections.add(
            _buildSection(
              context,
              'History',
              content?.history ?? '',
              _sectionKey(event, 'history'),
            ),
          );
        }
        if (_hasText(content?.scriptures)) {
          sections.add(
            _buildSection(
              context,
              'Scriptures',
              content?.scriptures ?? '',
              _sectionKey(event, 'scriptures'),
            ),
          );
        }
        if (_hasText(content?.pujaVidhi)) {
          sections.add(
            _buildSection(
              context,
              'Puja Vidhi',
              content?.pujaVidhi ?? '',
              _sectionKey(event, 'puja_vidhi'),
            ),
          );
        }
        if (event.rituals.isNotEmpty) {
          final ritualBody = event.rituals.map((ritual) => '• $ritual').join('\n');
          sections.add(
            _buildSection(
              context,
              'Rituals',
              ritualBody,
              _sectionKey(event, 'rituals'),
            ),
          );
        }
        if (event.faqs.isNotEmpty) {
          final faqBody = event.faqs
              .map((faq) => 'Q: ${faq.question}\nA: ${faq.answer}')
              .join('\n\n');
          sections.add(
            _buildSection(
              context,
              'FAQs',
              faqBody,
              _sectionKey(event, 'faqs'),
            ),
          );
        }

        final timings = snapshot.hasData
            ? _resolveMuhurats(snapshot.data!, event)
            : const <FestivalPujaMuhuratDto>[];

        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _displayName(event),
                style: AppThemes.headlineMd.copyWith(color: c.onSurface),
              ),
              if (_hasText(content?.subtitle)) ...[
                const SizedBox(height: 6),
                Text(
                  content?.subtitle ?? '',
                  style: AppThemes.bodyMd.copyWith(color: c.onSurfaceVariant),
                ),
              ],
              const SizedBox(height: 10),
              Row(
                children: [
                  _buildChip(_formatDate(event.date), c),
                  const SizedBox(width: 8),
                  _buildChip(_eventTypeLabel(event.type), c),
                ],
              ),
              const SizedBox(height: 14),
              if (snapshot.connectionState == ConnectionState.waiting)
                _buildTimingsPlaceholder(context, 'Loading timings...')
              else if (timings.isNotEmpty)
                _buildTimingsSection(context, timings),
              if (snapshot.connectionState != ConnectionState.waiting
                  && timings.isEmpty)
                _buildTimingsPlaceholder(
                  context,
                  'Timings are not available for this festival.',
                ),
              if (timings.isNotEmpty) const SizedBox(height: 4),
              if (sections.isEmpty)
                Text(
                  'Details are not available yet for this festival.',
                  style: AppThemes.bodyMd.copyWith(color: c.onSurfaceVariant),
                )
              else
                ..._withSectionSpacing(sections),
            ],
          ),
        );
      },
    );
  }

  void _primeDates(FestivalCalendarEventVm event) {
    _datesFutureForEvent(event);
  }

  Future<FestivalDatesResponseDto> _datesFutureForEvent(
    FestivalCalendarEventVm event,
  ) {
    final key = '${event.id}:${event.date.year}';
    return _datesCache.putIfAbsent(key, () {
      final api = ref.read(panchangApiProvider);
      final query = ref.read(dashboardQueryProvider);
      return api.fetchFestivalDates(
        event.id,
        query,
        year: event.date.year,
        includeChildren: true,
      );
    });
  }

  List<FestivalPujaMuhuratDto> _resolveMuhurats(
    FestivalDatesResponseDto data,
    FestivalCalendarEventVm event,
  ) {
    final variant = data.variants
        .where((item) => item.id == event.id)
        .toList();
    if (variant.isEmpty) {
      return [];
    }
    final dateKey = _formatIsoDate(event.date);
    final matches = variant.first.dates
        .where((item) => item.date == dateKey)
        .toList();
    FestivalDateOccurrenceDto? selected;
    if (matches.isNotEmpty) {
      selected = matches.firstWhere(
        (item) => item.primary == true,
        orElse: () => matches.first,
      );
    } else if (variant.first.dates.isNotEmpty) {
      selected = variant.first.dates.firstWhere(
        (item) => item.primary == true,
        orElse: () => variant.first.dates.first,
      );
    }
    return selected?.pujaMuhurats ?? [];
  }

  Widget _buildSection(
    BuildContext context,
    String title,
    String body,
    String key,
  ) {
    final c = AppColorsOf(context);
    final expanded = _expandedSections[key] ?? false;
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: c.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: c.border),
        boxShadow: [
          BoxShadow(
            color: c.primary.withOpacity(0.15),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: InkWell(
        onTap: () => _toggleSection(key),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: AppThemes.headlineSm.copyWith(color: c.onSurface),
                    ),
                  ),
                  Icon(
                    expanded ? Icons.expand_less : Icons.expand_more,
                    color: c.onSurfaceVariant,
                    size: 18,
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                body,
                maxLines: expanded ? null : 3,
                overflow:
                    expanded ? TextOverflow.visible : TextOverflow.ellipsis,
                style: AppThemes.bodyMd.copyWith(color: c.onSurfaceVariant),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTimingsSection(
    BuildContext context,
    List<FestivalPujaMuhuratDto> timings,
  ) {
    final c = AppColorsOf(context);
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: c.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: c.border),
        boxShadow: [
          BoxShadow(
            color: c.primary.withOpacity(0.08),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Timings',
              style: AppThemes.headlineSm.copyWith(color: c.onSurface),
            ),
            const SizedBox(height: 10),
            for (var i = 0; i < timings.length; i++) ...[
              _buildTimingRow(context, timings[i]),
              if (i != timings.length - 1)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  child: Divider(height: 1, color: c.border),
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTimingRow(
    BuildContext context,
    FestivalPujaMuhuratDto timing,
  ) {
    final c = AppColorsOf(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                timing.name,
                style: AppThemes.bodyMd.copyWith(color: c.onSurface),
              ),
            ),
            Text(
              _formatRange(timing.start, timing.end),
              style: AppThemes.bodyMd.copyWith(
                color: c.primaryContainer,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        if (_hasText(timing.description)) ...[
          const SizedBox(height: 6),
          Text(
            timing.description ?? '',
            style: AppThemes.bodySm.copyWith(color: c.onSurfaceVariant),
          ),
        ],
      ],
    );
  }

  Widget _buildTimingsPlaceholder(BuildContext context, String message) {
    final c = AppColorsOf(context);
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: c.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: c.border),
        boxShadow: [
          BoxShadow(
            color: c.primary.withOpacity(0.08),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Timings',
              style: AppThemes.headlineSm.copyWith(color: c.onSurface),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              style: AppThemes.bodyMd.copyWith(color: c.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }

  void _toggleSection(String key) {
    setState(() {
      _expandedSections[key] = !(_expandedSections[key] ?? false);
    });
  }

  String _sectionKey(FestivalCalendarEventVm event, String section) {
    return '${event.id}:${_formatIsoDate(event.date)}:$section';
  }

  Widget _buildChip(String text, AppColorsOf c) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: c.primaryContainer.withOpacity(0.1),
        borderRadius: BorderRadius.circular(100),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: c.primaryContainer,
        ),
      ),
    );
  }

  List<Widget> _withSectionSpacing(List<Widget> sections) {
    return sections;
  }

  String _formatDate(DateTime date) {
    final month = _monthName(date.month);
    return '$month ${date.day}, ${date.year}';
  }

  String _formatIsoDate(DateTime date) {
    final year = date.year.toString().padLeft(4, '0');
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '$year-$month-$day';
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

  String _eventTypeLabel(String? type) {
    if (type == null || type.trim().isEmpty) return 'Festival';
    return type.trim();
  }

  String _formatRange(String start, String end) {
    if (start.isEmpty || end.isEmpty) return '';
    return '$start - $end';
  }

  String _displayName(FestivalCalendarEventVm event) {
    final contentName = event.content?.name;
    if (contentName != null && contentName.trim().isNotEmpty) {
      return contentName.trim();
    }
    return _prettifyName(event.name);
  }

  String _prettifyName(String raw) {
    if (raw.trim().isEmpty) return raw;
    final base = raw.split('.').last;
    final words = base.replaceAll('-', ' ').split(RegExp(r'\s+'));
    final cleaned = words.where((w) => w.trim().isNotEmpty).map(_titleCase);
    return cleaned.join(' ');
  }

  String _titleCase(String word) {
    if (word.isEmpty) return word;
    final lower = word.toLowerCase();
    return lower[0].toUpperCase() + lower.substring(1);
  }

  bool _hasText(String? value) {
    return value != null && value.trim().isNotEmpty;
  }
}
