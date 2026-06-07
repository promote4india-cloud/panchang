class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'PANCHANG_API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// Read-only API key for all content endpoints.
  /// Injected at build time via `--dart-define=PANCHANG_USER_API_KEY=your_key`
  /// Never hard-code the value here — keep it in your CI/build config.
  static const String userApiKey = String.fromEnvironment(
    'PANCHANG_USER_API_KEY',
    defaultValue: '',
  );

  /// Authorization header map — empty when key is not configured (local dev).
  static Map<String, String> get authHeaders => userApiKey.isNotEmpty
      ? {'Authorization': 'Bearer $userApiKey'}
      : {};
}
