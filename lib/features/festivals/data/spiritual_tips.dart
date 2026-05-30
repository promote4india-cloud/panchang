const Map<String, String> spiritualTipsByHinduMonth = {
  'chaitra':
      'Chaitra: Beginning of the Hindu New Year, symbolizing renewal and fresh beginnings. Ideal for starting new goals, cleaning routines, practicing gratitude, and focusing on spiritual growth.',
  'vaishakh':
      'Vaishakh: A spiritually significant month associated with charity and purification. Recommended to donate food and water, stay disciplined, spend time in nature, and engage in spiritual reading.',
  'jyeshtha':
      'Jyeshtha: A month representing endurance and inner balance during intense summer heat. Focus on patience, staying calm, hydration, and helping people in need.',
  'ashadha':
      'Ashadha: Marks the beginning of monsoon and a period of introspection. Best suited for meditation, learning, reducing distractions, and strengthening spiritual discipline.',
  'shravana':
      'Shravana: A sacred month devoted to Lord Shiva and spiritual practices. Recommended to chant mantras, observe simplicity, visit temples, and practice self-control.',
  'bhadrapada':
      'Bhadrapada: Known for devotion and festivals like Ganesh Chaturthi, encouraging wisdom and humility. Good time to begin studies, creative work, worship Ganapati, and remove bad habits.',
  'ashwin':
      'Ashwin: Celebrates the victory of good over evil through Navratri and Dussehra. Focus on discipline, honoring feminine energy, and letting go of negativity.',
  'kartik':
      'Kartik: One of the holiest months, associated with Diwali and spiritual purification. Recommended to light lamps, perform charity, wake early, and cultivate purity of thought.',
  'margashirsha':
      'Margashirsha: A month connected with knowledge, devotion, and stability. Ideal for studying scriptures, strengthening family harmony, and maintaining consistent routines.',
  'pausha':
      'Pausha: A quiet winter month encouraging rest and reflection. Best for nourishing the body, conserving energy, planning ahead, and introspection.',
  'magha':
      'Magha: Spiritually powerful month for cleansing and discipline. Recommended to wake early, meditate, donate to others, and maintain healthy routines.',
  'phalguna':
      'Phalguna: A joyful month symbolizing love, forgiveness, and renewal through Holi celebrations. Focus on reconnecting with loved ones, forgiving past conflicts, and spreading positivity.',
};

const String defaultSpiritualTip =
    'Stay steady in your sadhana, keep gratitude at the center, and use this month to strengthen your spiritual routine.';

String spiritualTipForHinduMonth(String monthName) {
  final normalizedMonth = _normalizeHinduMonthName(monthName);
  return spiritualTipsByHinduMonth[normalizedMonth] ?? defaultSpiritualTip;
}

String _normalizeHinduMonthName(String monthName) {
  var value = monthName.toLowerCase().trim();
  value = value.replaceAll('adhik', '');
  value = value.replaceAll(RegExp(r'[^a-z]'), '');

  switch (value) {
    case 'kartika':
      return 'kartik';
    case 'shravan':
    case 'shravanam':
    case 'sravana':
      return 'shravana';
    case 'vaishakha':
      return 'vaishakh';
    case 'jyeshtha':
    case 'jyestha':
      return 'jyeshtha';
    case 'ashadha':
    case 'asadha':
      return 'ashadha';
    case 'bhadrapada':
    case 'bhadrapad':
      return 'bhadrapada';
    case 'margashirsha':
    case 'margasheersha':
    case 'margasirsha':
      return 'margashirsha';
    case 'pausha':
    case 'pushya':
      return 'pausha';
    case 'phalguna':
    case 'phalgun':
      return 'phalguna';
    default:
      return value;
  }
}
