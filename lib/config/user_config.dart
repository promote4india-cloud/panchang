class UserConfig {
  static const String _nameDefault = 'Aarav Sharma';
  static const String _genderDefault = 'male';
  static const String _birthDateDefault = '1992-08-14';
  static const String _birthTimeDefault = '06:45';
  static const String _birthPlaceDefault = 'Jaipur, Rajasthan, India';
  static const String _zodiacSignDefault = 'leo';
  static const String _traditionDefault = 'amanta';
  static const String _locationLabelDefault = 'Varanasi, India';

  static const double _latitudeDefault = 26.9124;
  static const double _longitudeDefault = 75.7873;
  static const String _timezoneDefault = 'Asia/Kolkata';
  static const String _languageDefault = 'en';

  static Map<String, dynamic> _overrides = const {};

  static Map<String, dynamic> get overrides => _overrides;

  static void applyOverrides(Map<String, dynamic> overrides) {
    _overrides = overrides;
  }

  static String get name => _string('name', _nameDefault);
  static String get gender => _string('gender', _genderDefault);
  static String get birthDate => _string('birthDate', _birthDateDefault);
  static String get birthTime => _string('birthTime', _birthTimeDefault);
  static String get birthPlace => _string('birthPlace', _birthPlaceDefault);
  static String get zodiacSign => _string('zodiacSign', _zodiacSignDefault);
  static String get tradition => _string('tradition', _traditionDefault);
  static String get locationLabel =>
      _string('locationLabel', _locationLabelDefault);

  static double get latitude => _double('latitude', _latitudeDefault);
  static double get longitude => _double('longitude', _longitudeDefault);
  static String get timezone => _string('timezone', _timezoneDefault);
  static String get language => _string('language', _languageDefault);

  static String _string(String key, String fallback) {
    final value = _overrides[key];
    if (value is String && value.trim().isNotEmpty) return value;
    return fallback;
  }

  static double _double(String key, double fallback) {
    final value = _overrides[key];
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? fallback;
    return fallback;
  }
}
