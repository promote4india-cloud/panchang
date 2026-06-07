# panchang_app

A new Flutter project.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Learn Flutter](https://docs.flutter.dev/get-started/learn-flutter)
- [Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Flutter learning resources](https://docs.flutter.dev/reference/learning-resources)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.


# Dev / run
flutter run \
  --dart-define=PANCHANG_API_BASE_URL=https://your-backend.onrender.com \
  --dart-define=PANCHANG_USER_API_KEY=your_user_key_here

# Release APK (Android)
flutter build apk \
  --dart-define=PANCHANG_API_BASE_URL=https://your-backend.onrender.com \
  --dart-define=PANCHANG_USER_API_KEY=your_user_key_here

# Release App Bundle (Play Store)
flutter build appbundle \
  --dart-define=PANCHANG_API_BASE_URL=https://your-backend.onrender.com \
  --dart-define=PANCHANG_USER_API_KEY=your_user_key_here

# Release IPA (iOS)
flutter build ipa \
  --dart-define=PANCHANG_API_BASE_URL=https://your-backend.onrender.com \
  --dart-define=PANCHANG_USER_API_KEY=your_user_key_here

