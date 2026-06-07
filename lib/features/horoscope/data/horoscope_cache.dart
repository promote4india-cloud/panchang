import '../models/horoscope_models.dart';

class _CacheEntry {
  final HoroscopePredictionDto data;
  final DateTime expiresAt;

  _CacheEntry({required this.data, required this.expiresAt});

  bool get isValid => DateTime.now().isBefore(expiresAt);
}

/// In-memory horoscope cache keyed by (sign, period, language).
///
/// Cache lifetime is tied to the current calendar window for each period
/// type — the entry expires the moment the window rolls over, not after a
/// fixed TTL.  This means:
///   daily / tomorrow  → midnight tonight / tomorrow night
///   weekly            → next Monday midnight
///   monthly           → first of next month
///   yearly            → first of next year
///
/// The cache is held for the lifetime of the app process.  On restart it
/// is empty; the first fetch for each (sign, period, language) tuple will
/// repopulate it and trigger background prefetching of the other two
/// standard periods (daily, weekly, monthly) for that sign.
class HoroscopeCache {
  HoroscopeCache._();
  static final HoroscopeCache instance = HoroscopeCache._();

  final _store = <String, _CacheEntry>{};

  String _key(String sign, String period, String language) =>
      '${sign}_${period}_$language';

  HoroscopePredictionDto? get(String sign, String period, String language) {
    final key = _key(sign, period, language);
    final entry = _store[key];
    if (entry == null) return null;
    if (!entry.isValid) {
      _store.remove(key);
      return null;
    }
    return entry.data;
  }

  void put(String sign, String period, String language, HoroscopePredictionDto data) {
    _store[_key(sign, period, language)] = _CacheEntry(
      data: data,
      expiresAt: _expiryFor(period),
    );
  }

  DateTime _expiryFor(String period) {
    final now = DateTime.now();
    switch (period) {
      case 'daily':
        // expires at next midnight
        return DateTime(now.year, now.month, now.day + 1);
      case 'tomorrow':
        // tomorrow's horoscope expires the midnight after tomorrow
        return DateTime(now.year, now.month, now.day + 2);
      case 'weekly':
      case 'weekly_love':
        // expires next Monday — (8 - weekday) is always 1..7
        return DateTime(now.year, now.month, now.day + (8 - now.weekday));
      case 'monthly':
        // expires first of next month
        return DateTime(now.year, now.month + 1, 1);
      case 'next_month':
        // expires first of the month after next
        return DateTime(now.year, now.month + 2, 1);
      case 'yearly':
        return DateTime(now.year + 1, 1, 1);
      default:
        return now.add(const Duration(hours: 1));
    }
  }
}
