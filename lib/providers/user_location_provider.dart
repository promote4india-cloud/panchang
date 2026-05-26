import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/user_config.dart';
import '../config/user_config_dev.dart';

class UserLocationSettings {
  final double latitude;
  final double longitude;
  final bool automaticDetection;

  const UserLocationSettings({
    required this.latitude,
    required this.longitude,
    required this.automaticDetection,
  });

  UserLocationSettings copyWith({
    double? latitude,
    double? longitude,
    bool? automaticDetection,
  }) {
    return UserLocationSettings(
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      automaticDetection: automaticDetection ?? this.automaticDetection,
    );
  }
}

const _prefLatitudeKey = 'user_location_latitude';
const _prefLongitudeKey = 'user_location_longitude';
const _prefAutoDetectKey = 'user_location_auto_detect';

class UserLocationNotifier extends AsyncNotifier<UserLocationSettings> {
  @override
  Future<UserLocationSettings> build() async {
    final prefs = await SharedPreferences.getInstance();
    final latitude = prefs.getDouble(_prefLatitudeKey) ?? UserConfig.latitude;
    final longitude = prefs.getDouble(_prefLongitudeKey) ?? UserConfig.longitude;
    final automaticDetection = prefs.getBool(_prefAutoDetectKey) ?? true;

    return UserLocationSettings(
      latitude: latitude,
      longitude: longitude,
      automaticDetection: automaticDetection,
    );
  }

  Future<void> setAutomaticDetection(bool enabled) async {
    final current = state.value ?? UserLocationSettings(
      latitude: UserConfig.latitude,
      longitude: UserConfig.longitude,
      automaticDetection: true,
    );
    final updated = current.copyWith(automaticDetection: enabled);
    state = AsyncData(updated);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefAutoDetectKey, enabled);
  }

  Future<void> setCoordinates(double latitude, double longitude) async {
    final current = state.value ?? UserLocationSettings(
      latitude: UserConfig.latitude,
      longitude: UserConfig.longitude,
      automaticDetection: true,
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
}

final userLocationProvider = AsyncNotifierProvider<UserLocationNotifier, UserLocationSettings>(() {
  return UserLocationNotifier();
});
