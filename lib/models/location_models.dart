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

/// Result from GET /v1/locations/resolve?lat=&lon=
/// Used after a GPS fix to get the IANA timezone and nearest city label.
class LocationResolveResult {
  /// IANA timezone string (e.g. "Asia/Kolkata").
  final String tz;

  /// Human-readable label for the nearest city (e.g. "Mumbai, Maharashtra, India").
  /// Null if no city was found within range (very remote area).
  final String? displayLabel;

  /// Raw lat/lon of the nearest city row in GeoNames (may differ slightly from GPS coords).
  final double? cityLat;
  final double? cityLon;

  const LocationResolveResult({
    required this.tz,
    this.displayLabel,
    this.cityLat,
    this.cityLon,
  });

  factory LocationResolveResult.fromJson(Map<String, dynamic> json) {
    final city = json['nearest_city'] as Map<String, dynamic>?;
    return LocationResolveResult(
      tz: json['tz'] as String? ?? 'Asia/Kolkata',
      displayLabel: city?['display_label'] as String?,
      cityLat: (city?['lat'] as num?)?.toDouble(),
      cityLon: (city?['lon'] as num?)?.toDouble(),
    );
  }
}

