// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Telugu (`te`).
class AppLocalizationsTe extends AppLocalizations {
  AppLocalizationsTe([String locale = 'te']) : super(locale);

  @override
  String get appTitle => 'వేద పంచాంగం';

  @override
  String get navPanchang => 'పంచాంగం';

  @override
  String get navHoroscope => 'రాశిఫలం';

  @override
  String get navFestivals => 'పండుగలు';

  @override
  String get navSettings => 'సెట్టింగ్‌లు';

  @override
  String get tithi => 'తిథి';

  @override
  String get sunrise => 'సూర్యోదయం';

  @override
  String get nakshatra => 'నక్షత్రం';

  @override
  String get sunset => 'సూర్యాస్తమయం';

  @override
  String get muhuratTimings => 'ముహూర్త సమయాలు';

  @override
  String get auspicious => 'శుభం';

  @override
  String get inauspicious => 'అశుభం';

  @override
  String get dailyRashifal => 'దైనిక రాశిఫలం';

  @override
  String get viewAll => 'అన్నీ చూడండి';

  @override
  String get upcomingEvents => 'రాబోయే పండుగలు';

  @override
  String get setReminder => 'రిమైండర్ సెట్ చేయండి';

  @override
  String get vratAndPujaVidhi => 'వ్రతం మరియు పూజా విధి';

  @override
  String get spiritualTip => 'ఆధ్యాత్మిక సూచన';

  @override
  String get spiritualTipFallback =>
      'ఈ నెలలో కృతజ్ఞతను పాటించండి మరియు మీ దినచర్యను స్థిరంగా ఉంచుకోండి.';

  @override
  String get festivalToday => 'ఈరోజు పండుగ';

  @override
  String get unableToLoadPanchang => 'పంచాంగం డేటాను లోడ్ చేయడం సాధ్యపడలేదు';

  @override
  String get retry => 'మళ్ళీ ప్రయత్నించండి';

  @override
  String get noUpcomingEvents => 'రాబోయే పండుగలు లేవు';

  @override
  String get sectionLocation => 'స్థానం';

  @override
  String get sectionReminders => 'రిమైండర్‌లు';

  @override
  String get sectionPreferences => 'ప్రాధాన్యతలు';

  @override
  String get automaticDetection => 'స్వయంచాలక గుర్తింపు';

  @override
  String get automaticDetectionSubtitle =>
      'ఖచ్చితమైన ముహూర్తం కోసం GPS ఉపయోగిస్తుంది';

  @override
  String get manualEntry => 'మాన్యువల్ ఎంట్రీ';

  @override
  String get dailyRahuKaal => 'దైనిక రాహు కాలం';

  @override
  String get dailyRahuKaalSubtitle => 'ప్రారంభానికి 15 నిమిషాల ముందు హెచ్చరిక';

  @override
  String get importantFestivals => 'ముఖ్యమైన పండుగలు';

  @override
  String get importantFestivalsSubtitle => 'ప్రధాన తిథులకు నోటిఫికేషన్‌లు';

  @override
  String get language => 'భాష';

  @override
  String get appearance => 'రూపం';

  @override
  String get privacyPolicy => 'గోప్యతా విధానం';

  @override
  String get termsOfService => 'సేవా నిబంధనలు';

  @override
  String get appVersion => 'వేద పంచాంగం v2.4.1 — విశ్వంతో సమన్వయం';

  @override
  String get vedicPractitioner => '2018 నుండి వేద సాధకుడు';

  @override
  String get searchLocation => 'స్థానాన్ని వెతకండి';

  @override
  String get searchHint => 'కనీసం 3 అక్షరాలు టైప్ చేయండి';

  @override
  String get enterMoreChars => '3 లేదా అంతకంటే ఎక్కువ అక్షరాలు నమోదు చేయండి.';

  @override
  String get noLocationsFound => 'స్థానాలు కనుగొనబడలేదు.';

  @override
  String get close => 'మూసివేయండి';

  @override
  String get cancel => 'రద్దు చేయండి';

  @override
  String get lightMode => 'లైట్ మోడ్';

  @override
  String get darkMode => 'డార్క్ మోడ్';

  @override
  String get systemDefault => 'సిస్టమ్ డిఫాల్ట్';

  @override
  String get horoscopeSubtitle =>
      'విశ్వ జ్ఞానంతో మీ రోజును సమన్వయపరచుకోండి. వేద చంద్ర క్యాలెండర్ ఆధారంగా అంచనాలు.';

  @override
  String get noHoroscopeAvailable => 'ఇప్పుడు రాశిఫలం అందుబాటులో లేదు.';

  @override
  String get noDetailsAvailable => 'ఇంకా వివరాలు అందుబాటులో లేవు.';

  @override
  String ratingFavorable(int percent) {
    return '$percent% అనుకూలంగా';
  }

  @override
  String predictionTitle(String sign) {
    return '$sign రాశిఫలం';
  }

  @override
  String horoscopeTitle(String duration) {
    return '$duration రాశిఫలం';
  }

  @override
  String get durationDaily => 'దైనిక';

  @override
  String get durationWeekly => 'వారపు';

  @override
  String get durationMonthly => 'మాసపు';

  @override
  String get categoryLove => 'ప్రేమ';

  @override
  String get categoryCareer => 'కెరీర్';

  @override
  String get categoryFinance => 'ఆర్థికం';

  @override
  String get categoryHealth => 'ఆరోగ్యం';

  @override
  String get categoryFamily => 'కుటుంబం';

  @override
  String get categoryWealth => 'సంపద';

  @override
  String get categoryMarriage => 'వివాహం';

  @override
  String get fullCalendarView => 'పూర్తి క్యాలెండర్ వీక్షణ';

  @override
  String get noFestivalsThisMonth => 'ఈ నెలలో పండుగలు లేవు.';

  @override
  String get unableToLoadFestivals => 'పండుగలు లోడ్ చేయడం సాధ్యపడలేదు.';

  @override
  String get featuredFestivals => 'విశేష పండుగలు';

  @override
  String get festival => 'పండుగ';

  @override
  String get selectLanguage => 'భాషను ఎంచుకోండి';

  @override
  String get daySunShort => 'ఆది';

  @override
  String get dayMonShort => 'సోమ';

  @override
  String get dayTueShort => 'మంగళ';

  @override
  String get dayWedShort => 'బుధ';

  @override
  String get dayThuShort => 'గురు';

  @override
  String get dayFriShort => 'శుక్ర';

  @override
  String get daySatShort => 'శని';

  @override
  String get dayMonFull => 'సోమ';

  @override
  String get dayTueFull => 'మంగళ';

  @override
  String get dayWedFull => 'బుధ';

  @override
  String get dayThuFull => 'గురు';

  @override
  String get dayFriFull => 'శుక్ర';

  @override
  String get daySatFull => 'శని';

  @override
  String get daySunFull => 'ఆది';

  @override
  String get monthJanShort => 'జన';

  @override
  String get monthFebShort => 'ఫిబ్ర';

  @override
  String get monthMarShort => 'మార్చి';

  @override
  String get monthAprShort => 'ఏప్ర';

  @override
  String get monthMayShort => 'మే';

  @override
  String get monthJunShort => 'జూన్';

  @override
  String get monthJulShort => 'జూల్';

  @override
  String get monthAugShort => 'ఆగ';

  @override
  String get monthSepShort => 'సెప్';

  @override
  String get monthOctShort => 'అక్ట';

  @override
  String get monthNovShort => 'నవ';

  @override
  String get monthDecShort => 'డిస';

  @override
  String get monthJanFull => 'జనవరి';

  @override
  String get monthFebFull => 'ఫిబ్రవరి';

  @override
  String get monthMarFull => 'మార్చి';

  @override
  String get monthAprFull => 'ఏప్రిల్';

  @override
  String get monthMayFull => 'మే';

  @override
  String get monthJunFull => 'జూన్';

  @override
  String get monthJulFull => 'జూలై';

  @override
  String get monthAugFull => 'ఆగస్టు';

  @override
  String get monthSepFull => 'సెప్టెంబర్';

  @override
  String get monthOctFull => 'అక్టోబర్';

  @override
  String get monthNovFull => 'నవంబర్';

  @override
  String get monthDecFull => 'డిసెంబర్';
}
