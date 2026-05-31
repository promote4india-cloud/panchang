import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/user_config.dart';
import '../config/user_config_dev.dart';

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

const _prefLatitudeKey = 'user_location_latitude';
const _prefLongitudeKey = 'user_location_longitude';
const _prefAutoDetectKey = 'user_location_auto_detect';
const _prefLocationLabelKey = 'user_location_label';
const _prefTimezoneKey = 'user_location_timezone';

class UserLocationNotifier extends AsyncNotifier<UserLocationSettings> {
  @override
  Future<UserLocationSettings> build() async {
    final prefs = await SharedPreferences.getInstance();
    final latitude = prefs.getDouble(_prefLatitudeKey) ?? UserConfig.latitude;
    final longitude =
        prefs.getDouble(_prefLongitudeKey) ?? UserConfig.longitude;
    final automaticDetection = prefs.getBool(_prefAutoDetectKey) ?? true;
    final label =
        prefs.getString(_prefLocationLabelKey) ?? UserConfig.locationLabel;
    final timezone = prefs.getString(_prefTimezoneKey) ?? UserConfig.timezone;

    return UserLocationSettings(
      latitude: latitude,
      longitude: longitude,
      automaticDetection: automaticDetection,
      label: label,
      timezone: timezone,
    );
  }

  Future<void> setAutomaticDetection(bool enabled) async {
    final current =
        state.value ??
        UserLocationSettings(
          latitude: UserConfig.latitude,
          longitude: UserConfig.longitude,
          automaticDetection: true,
          label: UserConfig.locationLabel,
          timezone: UserConfig.timezone,
        );
    final updated = current.copyWith(automaticDetection: enabled);
    state = AsyncData(updated);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefAutoDetectKey, enabled);
  }

  Future<void> setCoordinates(double latitude, double longitude) async {
    final current =
        state.value ??
        UserLocationSettings(
          latitude: UserConfig.latitude,
          longitude: UserConfig.longitude,
          automaticDetection: true,
          label: UserConfig.locationLabel,
          timezone: UserConfig.timezone,
        );
    final updated = current.copyWith(latitude: latitude, longitude: longitude);
    state = AsyncData(updated);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_prefLatitudeKey, latitude);
    await prefs.setDouble(_prefLongitudeKey, longitude);
    if (kDebugMode) {
      await UserConfigDevHelper.updateCoordinates(latitude, longitude);
    }
  }

  Future<void> setManualLocation({
    required double latitude,
    required double longitude,
    required String label,
    required String timezone,
  }) async {
    final current =
        state.value ??
        UserLocationSettings(
          latitude: UserConfig.latitude,
          longitude: UserConfig.longitude,
          automaticDetection: true,
          label: UserConfig.locationLabel,
          timezone: UserConfig.timezone,
        );
    final updated = current.copyWith(
      latitude: latitude,
      longitude: longitude,
      automaticDetection: false,
      label: label,
      timezone: timezone,
    );
    state = AsyncData(updated);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_prefLatitudeKey, latitude);
    await prefs.setDouble(_prefLongitudeKey, longitude);
    await prefs.setBool(_prefAutoDetectKey, false);
    await prefs.setString(_prefLocationLabelKey, label);
    await prefs.setString(_prefTimezoneKey, timezone);

    if (kDebugMode) {
      await UserConfigDevHelper.updateLocation(
        latitude: latitude,
        longitude: longitude,
        timezone: timezone,
        label: label,
      );
    }
  }
}

final userLocationProvider =
    AsyncNotifierProvider<UserLocationNotifier, UserLocationSettings>(() {
      return UserLocationNotifier();
    });
