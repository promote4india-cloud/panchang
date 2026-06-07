import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_bn.dart';
import 'app_localizations_en.dart';
import 'app_localizations_gu.dart';
import 'app_localizations_hi.dart';
import 'app_localizations_kn.dart';
import 'app_localizations_ml.dart';
import 'app_localizations_mr.dart';
import 'app_localizations_or.dart';
import 'app_localizations_pa.dart';
import 'app_localizations_sa.dart';
import 'app_localizations_ta.dart';
import 'app_localizations_te.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('bn'),
    Locale('en'),
    Locale('gu'),
    Locale('hi'),
    Locale('kn'),
    Locale('ml'),
    Locale('mr'),
    Locale('or'),
    Locale('pa'),
    Locale('sa'),
    Locale('ta'),
    Locale('te'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Vedic Panchang'**
  String get appTitle;

  /// No description provided for @navPanchang.
  ///
  /// In en, this message translates to:
  /// **'Panchang'**
  String get navPanchang;

  /// No description provided for @navHoroscope.
  ///
  /// In en, this message translates to:
  /// **'Horoscope'**
  String get navHoroscope;

  /// No description provided for @navFestivals.
  ///
  /// In en, this message translates to:
  /// **'Festivals'**
  String get navFestivals;

  /// No description provided for @navSettings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get navSettings;

  /// No description provided for @tithi.
  ///
  /// In en, this message translates to:
  /// **'Tithi'**
  String get tithi;

  /// No description provided for @sunrise.
  ///
  /// In en, this message translates to:
  /// **'Sunrise'**
  String get sunrise;

  /// No description provided for @nakshatra.
  ///
  /// In en, this message translates to:
  /// **'Nakshatra'**
  String get nakshatra;

  /// No description provided for @sunset.
  ///
  /// In en, this message translates to:
  /// **'Sunset'**
  String get sunset;

  /// No description provided for @muhuratTimings.
  ///
  /// In en, this message translates to:
  /// **'Muhurat Timings'**
  String get muhuratTimings;

  /// No description provided for @auspicious.
  ///
  /// In en, this message translates to:
  /// **'Auspicious'**
  String get auspicious;

  /// No description provided for @inauspicious.
  ///
  /// In en, this message translates to:
  /// **'Inauspicious'**
  String get inauspicious;

  /// No description provided for @dailyRashifal.
  ///
  /// In en, this message translates to:
  /// **'Daily Rashifal'**
  String get dailyRashifal;

  /// No description provided for @viewAll.
  ///
  /// In en, this message translates to:
  /// **'View All'**
  String get viewAll;

  /// No description provided for @upcomingEvents.
  ///
  /// In en, this message translates to:
  /// **'Upcoming Events'**
  String get upcomingEvents;

  /// No description provided for @setReminder.
  ///
  /// In en, this message translates to:
  /// **'Set Reminder'**
  String get setReminder;

  /// No description provided for @vratAndPujaVidhi.
  ///
  /// In en, this message translates to:
  /// **'Vrat and Puja Vidhi'**
  String get vratAndPujaVidhi;

  /// No description provided for @spiritualTip.
  ///
  /// In en, this message translates to:
  /// **'Spiritual Tip'**
  String get spiritualTip;

  /// No description provided for @spiritualTipFallback.
  ///
  /// In en, this message translates to:
  /// **'Practice gratitude and keep your routine steady this month.'**
  String get spiritualTipFallback;

  /// No description provided for @festivalToday.
  ///
  /// In en, this message translates to:
  /// **'Festival Today'**
  String get festivalToday;

  /// No description provided for @unableToLoadPanchang.
  ///
  /// In en, this message translates to:
  /// **'Unable to load Panchang data'**
  String get unableToLoadPanchang;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// No description provided for @noUpcomingEvents.
  ///
  /// In en, this message translates to:
  /// **'No upcoming events'**
  String get noUpcomingEvents;

  /// No description provided for @sectionLocation.
  ///
  /// In en, this message translates to:
  /// **'Location'**
  String get sectionLocation;

  /// No description provided for @sectionReminders.
  ///
  /// In en, this message translates to:
  /// **'Reminders'**
  String get sectionReminders;

  /// No description provided for @sectionPreferences.
  ///
  /// In en, this message translates to:
  /// **'Preferences'**
  String get sectionPreferences;

  /// No description provided for @automaticDetection.
  ///
  /// In en, this message translates to:
  /// **'Automatic Detection'**
  String get automaticDetection;

  /// No description provided for @automaticDetectionSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Uses GPS for precise Muhurta'**
  String get automaticDetectionSubtitle;

  /// No description provided for @manualEntry.
  ///
  /// In en, this message translates to:
  /// **'Manual Entry'**
  String get manualEntry;

  /// No description provided for @dailyRahuKaal.
  ///
  /// In en, this message translates to:
  /// **'Daily Rahu Kaal'**
  String get dailyRahuKaal;

  /// No description provided for @dailyRahuKaalSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Alert 15 mins before start'**
  String get dailyRahuKaalSubtitle;

  /// No description provided for @importantFestivals.
  ///
  /// In en, this message translates to:
  /// **'Important Festivals'**
  String get importantFestivals;

  /// No description provided for @importantFestivalsSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Notifications for major tithis'**
  String get importantFestivalsSubtitle;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @appearance.
  ///
  /// In en, this message translates to:
  /// **'Appearance'**
  String get appearance;

  /// No description provided for @privacyPolicy.
  ///
  /// In en, this message translates to:
  /// **'Privacy Policy'**
  String get privacyPolicy;

  /// No description provided for @termsOfService.
  ///
  /// In en, this message translates to:
  /// **'Terms of Service'**
  String get termsOfService;

  /// No description provided for @appVersion.
  ///
  /// In en, this message translates to:
  /// **'Vedic Panchang v2.4.1 — Alignment with the Cosmos'**
  String get appVersion;

  /// No description provided for @vedicPractitioner.
  ///
  /// In en, this message translates to:
  /// **'Vedic Practitioner since 2018'**
  String get vedicPractitioner;

  /// No description provided for @searchLocation.
  ///
  /// In en, this message translates to:
  /// **'Search Location'**
  String get searchLocation;

  /// No description provided for @searchHint.
  ///
  /// In en, this message translates to:
  /// **'Type at least 3 characters'**
  String get searchHint;

  /// No description provided for @enterMoreChars.
  ///
  /// In en, this message translates to:
  /// **'Enter 3 or more characters.'**
  String get enterMoreChars;

  /// No description provided for @noLocationsFound.
  ///
  /// In en, this message translates to:
  /// **'No locations found.'**
  String get noLocationsFound;

  /// No description provided for @close.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get close;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @lightMode.
  ///
  /// In en, this message translates to:
  /// **'Light Mode'**
  String get lightMode;

  /// No description provided for @darkMode.
  ///
  /// In en, this message translates to:
  /// **'Dark Mode'**
  String get darkMode;

  /// No description provided for @systemDefault.
  ///
  /// In en, this message translates to:
  /// **'System Default'**
  String get systemDefault;

  /// No description provided for @horoscopeSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Align your day with cosmic wisdom. Predictions based on the Vedic Lunar Calendar.'**
  String get horoscopeSubtitle;

  /// No description provided for @noHoroscopeAvailable.
  ///
  /// In en, this message translates to:
  /// **'No horoscope available right now.'**
  String get noHoroscopeAvailable;

  /// No description provided for @noDetailsAvailable.
  ///
  /// In en, this message translates to:
  /// **'No details available yet.'**
  String get noDetailsAvailable;

  /// No description provided for @ratingFavorable.
  ///
  /// In en, this message translates to:
  /// **'{percent}% Favorable'**
  String ratingFavorable(int percent);

  /// No description provided for @predictionTitle.
  ///
  /// In en, this message translates to:
  /// **'{sign} Prediction'**
  String predictionTitle(String sign);

  /// No description provided for @horoscopeTitle.
  ///
  /// In en, this message translates to:
  /// **'{duration} Horoscope'**
  String horoscopeTitle(String duration);

  /// No description provided for @durationDaily.
  ///
  /// In en, this message translates to:
  /// **'Daily'**
  String get durationDaily;

  /// No description provided for @durationWeekly.
  ///
  /// In en, this message translates to:
  /// **'Weekly'**
  String get durationWeekly;

  /// No description provided for @durationMonthly.
  ///
  /// In en, this message translates to:
  /// **'Monthly'**
  String get durationMonthly;

  /// No description provided for @categoryLove.
  ///
  /// In en, this message translates to:
  /// **'Love'**
  String get categoryLove;

  /// No description provided for @categoryCareer.
  ///
  /// In en, this message translates to:
  /// **'Career'**
  String get categoryCareer;

  /// No description provided for @categoryFinance.
  ///
  /// In en, this message translates to:
  /// **'Finance'**
  String get categoryFinance;

  /// No description provided for @categoryHealth.
  ///
  /// In en, this message translates to:
  /// **'Health'**
  String get categoryHealth;

  /// No description provided for @categoryFamily.
  ///
  /// In en, this message translates to:
  /// **'Family'**
  String get categoryFamily;

  /// No description provided for @categoryWealth.
  ///
  /// In en, this message translates to:
  /// **'Wealth'**
  String get categoryWealth;

  /// No description provided for @categoryMarriage.
  ///
  /// In en, this message translates to:
  /// **'Marriage'**
  String get categoryMarriage;

  /// No description provided for @fullCalendarView.
  ///
  /// In en, this message translates to:
  /// **'Full Calendar View'**
  String get fullCalendarView;

  /// No description provided for @noFestivalsThisMonth.
  ///
  /// In en, this message translates to:
  /// **'No festivals listed for this month.'**
  String get noFestivalsThisMonth;

  /// No description provided for @unableToLoadFestivals.
  ///
  /// In en, this message translates to:
  /// **'Unable to load festivals.'**
  String get unableToLoadFestivals;

  /// No description provided for @featuredFestivals.
  ///
  /// In en, this message translates to:
  /// **'Featured Festivals'**
  String get featuredFestivals;

  /// No description provided for @festival.
  ///
  /// In en, this message translates to:
  /// **'Festival'**
  String get festival;

  /// No description provided for @selectLanguage.
  ///
  /// In en, this message translates to:
  /// **'Select Language'**
  String get selectLanguage;

  /// No description provided for @daySunShort.
  ///
  /// In en, this message translates to:
  /// **'SUN'**
  String get daySunShort;

  /// No description provided for @dayMonShort.
  ///
  /// In en, this message translates to:
  /// **'MON'**
  String get dayMonShort;

  /// No description provided for @dayTueShort.
  ///
  /// In en, this message translates to:
  /// **'TUE'**
  String get dayTueShort;

  /// No description provided for @dayWedShort.
  ///
  /// In en, this message translates to:
  /// **'WED'**
  String get dayWedShort;

  /// No description provided for @dayThuShort.
  ///
  /// In en, this message translates to:
  /// **'THU'**
  String get dayThuShort;

  /// No description provided for @dayFriShort.
  ///
  /// In en, this message translates to:
  /// **'FRI'**
  String get dayFriShort;

  /// No description provided for @daySatShort.
  ///
  /// In en, this message translates to:
  /// **'SAT'**
  String get daySatShort;

  /// No description provided for @dayMonFull.
  ///
  /// In en, this message translates to:
  /// **'Mon'**
  String get dayMonFull;

  /// No description provided for @dayTueFull.
  ///
  /// In en, this message translates to:
  /// **'Tue'**
  String get dayTueFull;

  /// No description provided for @dayWedFull.
  ///
  /// In en, this message translates to:
  /// **'Wed'**
  String get dayWedFull;

  /// No description provided for @dayThuFull.
  ///
  /// In en, this message translates to:
  /// **'Thu'**
  String get dayThuFull;

  /// No description provided for @dayFriFull.
  ///
  /// In en, this message translates to:
  /// **'Fri'**
  String get dayFriFull;

  /// No description provided for @daySatFull.
  ///
  /// In en, this message translates to:
  /// **'Sat'**
  String get daySatFull;

  /// No description provided for @daySunFull.
  ///
  /// In en, this message translates to:
  /// **'Sun'**
  String get daySunFull;

  /// No description provided for @monthJanShort.
  ///
  /// In en, this message translates to:
  /// **'Jan'**
  String get monthJanShort;

  /// No description provided for @monthFebShort.
  ///
  /// In en, this message translates to:
  /// **'Feb'**
  String get monthFebShort;

  /// No description provided for @monthMarShort.
  ///
  /// In en, this message translates to:
  /// **'Mar'**
  String get monthMarShort;

  /// No description provided for @monthAprShort.
  ///
  /// In en, this message translates to:
  /// **'Apr'**
  String get monthAprShort;

  /// No description provided for @monthMayShort.
  ///
  /// In en, this message translates to:
  /// **'May'**
  String get monthMayShort;

  /// No description provided for @monthJunShort.
  ///
  /// In en, this message translates to:
  /// **'Jun'**
  String get monthJunShort;

  /// No description provided for @monthJulShort.
  ///
  /// In en, this message translates to:
  /// **'Jul'**
  String get monthJulShort;

  /// No description provided for @monthAugShort.
  ///
  /// In en, this message translates to:
  /// **'Aug'**
  String get monthAugShort;

  /// No description provided for @monthSepShort.
  ///
  /// In en, this message translates to:
  /// **'Sep'**
  String get monthSepShort;

  /// No description provided for @monthOctShort.
  ///
  /// In en, this message translates to:
  /// **'Oct'**
  String get monthOctShort;

  /// No description provided for @monthNovShort.
  ///
  /// In en, this message translates to:
  /// **'Nov'**
  String get monthNovShort;

  /// No description provided for @monthDecShort.
  ///
  /// In en, this message translates to:
  /// **'Dec'**
  String get monthDecShort;

  /// No description provided for @monthJanFull.
  ///
  /// In en, this message translates to:
  /// **'January'**
  String get monthJanFull;

  /// No description provided for @monthFebFull.
  ///
  /// In en, this message translates to:
  /// **'February'**
  String get monthFebFull;

  /// No description provided for @monthMarFull.
  ///
  /// In en, this message translates to:
  /// **'March'**
  String get monthMarFull;

  /// No description provided for @monthAprFull.
  ///
  /// In en, this message translates to:
  /// **'April'**
  String get monthAprFull;

  /// No description provided for @monthMayFull.
  ///
  /// In en, this message translates to:
  /// **'May'**
  String get monthMayFull;

  /// No description provided for @monthJunFull.
  ///
  /// In en, this message translates to:
  /// **'June'**
  String get monthJunFull;

  /// No description provided for @monthJulFull.
  ///
  /// In en, this message translates to:
  /// **'July'**
  String get monthJulFull;

  /// No description provided for @monthAugFull.
  ///
  /// In en, this message translates to:
  /// **'August'**
  String get monthAugFull;

  /// No description provided for @monthSepFull.
  ///
  /// In en, this message translates to:
  /// **'September'**
  String get monthSepFull;

  /// No description provided for @monthOctFull.
  ///
  /// In en, this message translates to:
  /// **'October'**
  String get monthOctFull;

  /// No description provided for @monthNovFull.
  ///
  /// In en, this message translates to:
  /// **'November'**
  String get monthNovFull;

  /// No description provided for @monthDecFull.
  ///
  /// In en, this message translates to:
  /// **'December'**
  String get monthDecFull;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) => <String>[
    'bn',
    'en',
    'gu',
    'hi',
    'kn',
    'ml',
    'mr',
    'or',
    'pa',
    'sa',
    'ta',
    'te',
  ].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'bn':
      return AppLocalizationsBn();
    case 'en':
      return AppLocalizationsEn();
    case 'gu':
      return AppLocalizationsGu();
    case 'hi':
      return AppLocalizationsHi();
    case 'kn':
      return AppLocalizationsKn();
    case 'ml':
      return AppLocalizationsMl();
    case 'mr':
      return AppLocalizationsMr();
    case 'or':
      return AppLocalizationsOr();
    case 'pa':
      return AppLocalizationsPa();
    case 'sa':
      return AppLocalizationsSa();
    case 'ta':
      return AppLocalizationsTa();
    case 'te':
      return AppLocalizationsTe();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
