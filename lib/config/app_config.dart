class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'PANCHANG_API_BASE_URL',
    defaultValue: 'http://localhost:8080',
  );

}
