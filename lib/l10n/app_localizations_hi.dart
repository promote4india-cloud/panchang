// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Hindi (`hi`).
class AppLocalizationsHi extends AppLocalizations {
  AppLocalizationsHi([String locale = 'hi']) : super(locale);

  @override
  String get appTitle => 'वैदिक पंचांग';

  @override
  String get navPanchang => 'पंचांग';

  @override
  String get navHoroscope => 'राशिफल';

  @override
  String get navFestivals => 'त्योहार';

  @override
  String get navSettings => 'सेटिंग्स';

  @override
  String get tithi => 'तिथि';

  @override
  String get sunrise => 'सूर्योदय';

  @override
  String get nakshatra => 'नक्षत्र';

  @override
  String get sunset => 'सूर्यास्त';

  @override
  String get muhuratTimings => 'मुहूर्त समय';

  @override
  String get auspicious => 'शुभ';

  @override
  String get inauspicious => 'अशुभ';

  @override
  String get dailyRashifal => 'दैनिक राशिफल';

  @override
  String get viewAll => 'सभी देखें';

  @override
  String get upcomingEvents => 'आगामी त्योहार';

  @override
  String get setReminder => 'रिमाइंडर सेट करें';

  @override
  String get vratAndPujaVidhi => 'व्रत और पूजा विधि';

  @override
  String get spiritualTip => 'आध्यात्मिक सुझाव';

  @override
  String get spiritualTipFallback =>
      'इस माह कृतज्ञता का अभ्यास करें और अपनी दिनचर्या को स्थिर रखें।';

  @override
  String get festivalToday => 'आज का त्योहार';

  @override
  String get unableToLoadPanchang => 'पंचांग डेटा लोड करने में असमर्थ';

  @override
  String get retry => 'पुनः प्रयास करें';

  @override
  String get noUpcomingEvents => 'कोई आगामी त्योहार नहीं';

  @override
  String get sectionLocation => 'स्थान';

  @override
  String get sectionReminders => 'रिमाइंडर';

  @override
  String get sectionPreferences => 'प्राथमिकताएं';

  @override
  String get automaticDetection => 'स्वचालित पहचान';

  @override
  String get automaticDetectionSubtitle => 'सटीक मुहूर्त के लिए GPS उपयोग';

  @override
  String get manualEntry => 'मैन्युअल प्रविष्टि';

  @override
  String get dailyRahuKaal => 'दैनिक राहु काल';

  @override
  String get dailyRahuKaalSubtitle => 'शुरू होने से 15 मिनट पहले अलर्ट';

  @override
  String get importantFestivals => 'महत्वपूर्ण त्योहार';

  @override
  String get importantFestivalsSubtitle => 'प्रमुख तिथियों की सूचनाएं';

  @override
  String get language => 'भाषा';

  @override
  String get appearance => 'रूप-रंग';

  @override
  String get privacyPolicy => 'गोपनीयता नीति';

  @override
  String get termsOfService => 'सेवा की शर्तें';

  @override
  String get appVersion => 'वैदिक पंचांग v2.4.1 — ब्रह्माण्ड के साथ संरेखण';

  @override
  String get vedicPractitioner => '2018 से वैदिक साधक';

  @override
  String get searchLocation => 'स्थान खोजें';

  @override
  String get searchHint => 'कम से कम 3 अक्षर टाइप करें';

  @override
  String get enterMoreChars => '3 या अधिक अक्षर दर्ज करें।';

  @override
  String get noLocationsFound => 'कोई स्थान नहीं मिला।';

  @override
  String get close => 'बंद करें';

  @override
  String get cancel => 'रद्द करें';

  @override
  String get lightMode => 'लाइट मोड';

  @override
  String get darkMode => 'डार्क मोड';

  @override
  String get systemDefault => 'सिस्टम डिफ़ॉल्ट';

  @override
  String get horoscopeSubtitle =>
      'ब्रह्माण्डीय ज्ञान के साथ अपना दिन संरेखित करें। वैदिक चंद्र कैलेंडर पर आधारित भविष्यवाणियां।';

  @override
  String get noHoroscopeAvailable => 'अभी कोई राशिफल उपलब्ध नहीं।';

  @override
  String get noDetailsAvailable => 'अभी विवरण उपलब्ध नहीं।';

  @override
  String ratingFavorable(int percent) {
    return '$percent% अनुकूल';
  }

  @override
  String predictionTitle(String sign) {
    return '$sign राशिफल';
  }

  @override
  String horoscopeTitle(String duration) {
    return '$duration राशिफल';
  }

  @override
  String get durationDaily => 'दैनिक';

  @override
  String get durationWeekly => 'साप्ताहिक';

  @override
  String get durationMonthly => 'मासिक';

  @override
  String get categoryLove => 'प्रेम';

  @override
  String get categoryCareer => 'करियर';

  @override
  String get categoryFinance => 'वित्त';

  @override
  String get categoryHealth => 'स्वास्थ्य';

  @override
  String get categoryFamily => 'परिवार';

  @override
  String get categoryWealth => 'धन';

  @override
  String get categoryMarriage => 'विवाह';

  @override
  String get fullCalendarView => 'पूर्ण कैलेंडर दृश्य';

  @override
  String get noFestivalsThisMonth => 'इस माह कोई त्योहार नहीं।';

  @override
  String get unableToLoadFestivals => 'त्योहार लोड करने में असमर्थ।';

  @override
  String get featuredFestivals => 'विशेष त्योहार';

  @override
  String get festival => 'त्योहार';

  @override
  String get selectLanguage => 'भाषा चुनें';

  @override
  String get daySunShort => 'रवि';

  @override
  String get dayMonShort => 'सोम';

  @override
  String get dayTueShort => 'मंगल';

  @override
  String get dayWedShort => 'बुध';

  @override
  String get dayThuShort => 'गुरु';

  @override
  String get dayFriShort => 'शुक्र';

  @override
  String get daySatShort => 'शनि';

  @override
  String get dayMonFull => 'सोम';

  @override
  String get dayTueFull => 'मंगल';

  @override
  String get dayWedFull => 'बुध';

  @override
  String get dayThuFull => 'गुरु';

  @override
  String get dayFriFull => 'शुक्र';

  @override
  String get daySatFull => 'शनि';

  @override
  String get daySunFull => 'रवि';

  @override
  String get monthJanShort => 'जन';

  @override
  String get monthFebShort => 'फर';

  @override
  String get monthMarShort => 'मार्च';

  @override
  String get monthAprShort => 'अप्रैल';

  @override
  String get monthMayShort => 'मई';

  @override
  String get monthJunShort => 'जून';

  @override
  String get monthJulShort => 'जुल';

  @override
  String get monthAugShort => 'अग';

  @override
  String get monthSepShort => 'सित';

  @override
  String get monthOctShort => 'अक्ट';

  @override
  String get monthNovShort => 'नव';

  @override
  String get monthDecShort => 'दिस';

  @override
  String get monthJanFull => 'जनवरी';

  @override
  String get monthFebFull => 'फरवरी';

  @override
  String get monthMarFull => 'मार्च';

  @override
  String get monthAprFull => 'अप्रैल';

  @override
  String get monthMayFull => 'मई';

  @override
  String get monthJunFull => 'जून';

  @override
  String get monthJulFull => 'जुलाई';

  @override
  String get monthAugFull => 'अगस्त';

  @override
  String get monthSepFull => 'सितंबर';

  @override
  String get monthOctFull => 'अक्टूबर';

  @override
  String get monthNovFull => 'नवंबर';

  @override
  String get monthDecFull => 'दिसंबर';
}
