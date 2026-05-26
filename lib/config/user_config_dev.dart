import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import 'user_config.dart';

class UserConfigDevHelper {
  static const String _assetPath = 'assets/user_config.dev.json';
  static const String _fileName = 'user_config.dev.json';

  static Future<void> loadOverrides() async {
    if (!kDebugMode) return;

    final overrides = await _loadFromLocalFile() ?? await _loadFromAsset();
    if (overrides != null) {
      UserConfig.applyOverrides(overrides);
    }
  }

  static Future<void> updateCoordinates(double latitude, double longitude) async {
    if (!kDebugMode) return;

    final updated = Map<String, dynamic>.from(UserConfig.overrides);
    updated['latitude'] = latitude;
    updated['longitude'] = longitude;
    await saveOverrides(updated);
  }

  static Future<void> saveOverrides(Map<String, dynamic> overrides) async {
    if (!kDebugMode) return;

    final file = await _localFile();
    final payload = const JsonEncoder.withIndent('  ').convert(overrides);
    await file.writeAsString(payload);
    UserConfig.applyOverrides(overrides);
  }

  static Future<Map<String, dynamic>?> _loadFromLocalFile() async {
    try {
      final file = await _localFile();
      if (!await file.exists()) return null;
      final content = await file.readAsString();
      final decoded = jsonDecode(content);
      if (decoded is Map<String, dynamic>) return decoded;
    } catch (_) {
      return null;
    }
    return null;
  }

  static Future<Map<String, dynamic>?> _loadFromAsset() async {
    try {
      final content = await rootBundle.loadString(_assetPath);
      final decoded = jsonDecode(content);
      if (decoded is Map<String, dynamic>) return decoded;
    } catch (_) {
      return null;
    }
    return null;
  }

  static Future<File> _localFile() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/$_fileName');
  }
}
