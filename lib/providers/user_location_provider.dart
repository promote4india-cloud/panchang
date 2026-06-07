import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config.dart';
import '../config/user_config.dart';
import '../config/user_config_dev.dart';
import '../features/panchang/data/panchang_api.dart';

// ---------------------------------------------------------------------------
// Preference keys
// ---------------------------------------------------------------------------
const _prefLatitudeKey = 'user_location_latitude';
const _prefLongitudeKey = 'user_location_longitude';
const _prefAutoDetectKey = 'user_location_auto_detect';
const _prefLocationLabelKey = 'user_location_label';
const _prefTimezoneKey = 'user_location_timezone';

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

class UserLocationSettings {
  final double latitude;
  final double longitude;
  final bool automaticDetection;
  final String label;
  final String timezone;

  const UserLocationSettings({
    required this.latitude,
    required this.longitude,
    required this.automaticDetection,
    required this.label,
    required this.timezone,
  });

  UserLocationSettings copyWith({
    double? latitude,
    double? longitude,
    bool? automaticDetection,
    String? label,
    String? timezone,
  }) {
    return UserLocationSettings(
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      automaticDetection: automaticDetection ?? this.automaticDetection,
      label: label ?? this.label,
      timezone: timezone ?? this.timezone,
    );
  }
}

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class UserLocationNotifier extends AsyncNotifier<UserLocationSettings> {
  // ---- Build / startup ----------------------------------------------------

  @override
  Future<UserLocationSettings> build() async {
    final prefs = await SharedPreferences.getInstance();

    final savedLat = prefs.getDouble(_prefLatitudeKey);
    final savedLon = prefs.getDouble(_prefLongitudeKey);
    final autoDetect = prefs.getBool(_prefAutoDetectKey) ?? true;
    final label = prefs.getString(_prefLocationLabelKey) ?? UserConfig.locationLabel;
    final timezone = prefs.getString(_prefTimezoneKey) ?? UserConfig.timezone;

    // If we have stored GPS coords, use them immediately (fast startup).
    // The user can always re-tap the toggle to trigger a fresh GPS fix.
    if (savedLat != null && savedLon != null) {
      return UserLocationSettings(
        latitude: savedLat,
        longitude: savedLon,
        automaticDetection: autoDetect,
        label: label,
        timezone: timezone,
      );
    }

    // First launch with auto-detect ON and no stored coords → run GPS now.
    if (autoDetect) {
      // Return defaults immediately so the UI doesn't block,
      // then kick off detection asynchronously.
      Future.microtask(() => detectAndResolve());
    }

    return UserLocationSettings(
      latitude: UserConfig.latitude,
      longitude: UserConfig.longitude,
      automaticDetection: autoDetect,
      label: label,
      timezone: timezone,
    );
  }

  // ---- GPS → Reverse-geocode → Save  (the core pipeline) -----------------

  /// Full automatic location pipeline:
  ///   1. Check & request GPS permission
  ///   2. Obtain GPS fix via Geolocator
  ///   3. Call GET /v1/locations/resolve to get IANA timezone + city label
  ///   4. Persist everything to SharedPreferences
  ///   5. Emit updated state → all downstream providers refetch
  ///
  /// Throws a [LocationDetectionError] on any failure so the caller
  /// (settings screen) can show the appropriate error message.
  Future<void> detectAndResolve() async {
    // Mark loading while we are working — keeps the toggle in "busy" state
    final current = state.value ?? _defaults();
    state = AsyncLoading();

    try {
      // 1. GPS permission
      final permissionOk = await _ensurePermission();
      if (!permissionOk) {
        // Restore previous state; do not disable auto-detect (user might retry)
        state = AsyncData(current);
        throw const LocationDetectionError('Location permission denied.');
      }

      // 2. GPS position
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 15),
        ),
      );

      // 3. Reverse-geocode via backend
      final api = PanchangApiClient(baseUrl: AppConfig.apiBaseUrl);
      final resolved = await api.resolveLocation(
        lat: position.latitude,
        lon: position.longitude,
      );

      // 4. Build the new settings
      final label = resolved.displayLabel ?? current.label;
      final updated = UserLocationSettings(
        latitude: position.latitude,
        longitude: position.longitude,
        automaticDetection: true,
        label: label,
        timezone: resolved.tz,
      );

      // 5. Persist
      await _persist(updated);

      // Debug helper
      if (kDebugMode) {
        await UserConfigDevHelper.updateLocation(
          latitude: updated.latitude,
          longitude: updated.longitude,
          timezone: updated.timezone,
          label: updated.label,
        );
      }

      state = AsyncData(updated);
    } catch (e) {
      // On any error restore the previous (working) state
      state = AsyncData(current);
      if (e is LocationDetectionError) rethrow;
      throw LocationDetectionError(e.toString());
    }
  }

  // ---- Toggle auto-detect ON/OFF ------------------------------------------

  Future<void> setAutomaticDetection(bool enabled) async {
    final current = state.value ?? _defaults();
    final updated = current.copyWith(automaticDetection: enabled);
    state = AsyncData(updated);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefAutoDetectKey, enabled);

    // Kick off GPS detection when user enables the toggle
    if (enabled) {
      await detectAndResolve();
    }
  }

  // ---- Manual location (search dialog) ------------------------------------

  Future<void> setManualLocation({
    required double latitude,
    required double longitude,
    required String label,
    required String timezone,
  }) async {
    final updated = UserLocationSettings(
      latitude: latitude,
      longitude: longitude,
      automaticDetection: false,
      label: label,
      timezone: timezone,
    );
    state = AsyncData(updated);

    await _persist(updated);

    if (kDebugMode) {
      await UserConfigDevHelper.updateLocation(
        latitude: latitude,
        longitude: longitude,
        timezone: timezone,
        label: label,
      );
    }
  }

  // ---- Helpers ------------------------------------------------------------

  UserLocationSettings _defaults() => UserLocationSettings(
        latitude: UserConfig.latitude,
        longitude: UserConfig.longitude,
        automaticDetection: true,
        label: UserConfig.locationLabel,
        timezone: UserConfig.timezone,
      );

  Future<void> _persist(UserLocationSettings s) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_prefLatitudeKey, s.latitude);
    await prefs.setDouble(_prefLongitudeKey, s.longitude);
    await prefs.setBool(_prefAutoDetectKey, s.automaticDetection);
    await prefs.setString(_prefLocationLabelKey, s.label);
    await prefs.setString(_prefTimezoneKey, s.timezone);
  }

  Future<bool> _ensurePermission() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return false;

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    return permission != LocationPermission.denied &&
        permission != LocationPermission.deniedForever;
  }
}

// ---------------------------------------------------------------------------
// Typed error so callers can show user-friendly messages
// ---------------------------------------------------------------------------

class LocationDetectionError implements Exception {
  final String message;
  const LocationDetectionError(this.message);

  @override
  String toString() => message;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

final userLocationProvider =
    AsyncNotifierProvider<UserLocationNotifier, UserLocationSettings>(() {
  return UserLocationNotifier();
});
