class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'PANCHANG_API_BASE_URL',
    defaultValue: 'https://panchang-mo63.onrender.com',
  );

}
