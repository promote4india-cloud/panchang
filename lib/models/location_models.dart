class LocationSearchResult {
  final int id;
  final String name;
  final String? nameLocalized;
  final String? admin2;
  final String? admin1;
  final String? admin1Localized;
  final String country;
  final String? countryLocalized;
  final double lat;
  final double lon;
  final String tz;
  final int? population;
  final String? featureCode;
  final String displayLabel;

  LocationSearchResult({
    required this.id,
    required this.name,
    required this.nameLocalized,
    required this.admin2,
    required this.admin1,
    required this.admin1Localized,
    required this.country,
    required this.countryLocalized,
    required this.lat,
    required this.lon,
    required this.tz,
    required this.population,
    required this.featureCode,
    required this.displayLabel,
  });

  factory LocationSearchResult.fromJson(Map<String, dynamic> json) {
    return LocationSearchResult(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      nameLocalized: json['name_localized'] as String?,
      admin2: json['admin2'] as String?,
      admin1: json['admin1'] as String?,
      admin1Localized: json['admin1_localized'] as String?,
      country: json['country'] as String? ?? '',
      countryLocalized: json['country_localized'] as String?,
      lat: (json['lat'] as num?)?.toDouble() ?? 0,
      lon: (json['lon'] as num?)?.toDouble() ?? 0,
      tz: json['tz'] as String? ?? '',
      population: json['population'] as int?,
      featureCode: json['feature_code'] as String?,
      displayLabel: json['display_label'] as String? ?? '',
    );
  }

  String subtitleLabel() {
    final adminLabel = admin1Localized?.trim().isNotEmpty == true
        ? admin1Localized!
        : (admin1 ?? '').trim();
    if (adminLabel.isNotEmpty) return adminLabel;
    return (countryLocalized?.trim().isNotEmpty == true
            ? countryLocalized
            : country)
        .toString();
  }
}
