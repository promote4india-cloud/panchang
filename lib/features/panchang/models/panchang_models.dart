class PanchangTodayDto {
  final String date;
  final String weekday;
  final TithiDto tithi;
  final NakshatraDto nakshatra;
  final MasaDto masa;
  final SunMoonDto sunMoon;
  final HinduMonthYearDto hinduMonthAndYear;

  PanchangTodayDto({
    required this.date,
    required this.weekday,
    required this.tithi,
    required this.nakshatra,
    required this.masa,
    required this.sunMoon,
    required this.hinduMonthAndYear,
  });

  factory PanchangTodayDto.fromJson(Map<String, dynamic> json) {
    return PanchangTodayDto(
      date: json['date'] as String,
      weekday: json['weekday'] as String,
      tithi: TithiDto.fromJson(json['tithi'] as Map<String, dynamic>),
      nakshatra: NakshatraDto.fromJson(json['nakshatra'] as Map<String, dynamic>),
      masa: MasaDto.fromJson(json['masa'] as Map<String, dynamic>),
      sunMoon: SunMoonDto.fromJson(json['sun_moon'] as Map<String, dynamic>),
      hinduMonthAndYear: HinduMonthYearDto.fromJson(
        json['hindu_month_and_year'] as Map<String, dynamic>,
      ),
    );
  }
}

class HinduMonthYearDto {
  final String monthPurnimanta;
  final String monthAmanta;

  HinduMonthYearDto({
    required this.monthPurnimanta,
    required this.monthAmanta,
  });

  factory HinduMonthYearDto.fromJson(Map<String, dynamic> json) {
    return HinduMonthYearDto(
      monthPurnimanta: json['month_purnimanta'] as String? ?? '',
      monthAmanta: json['month_amanta'] as String? ?? '',
    );
  }
}

class TithiDto {
  final String name;
  final String paksha;
  final String endsAtLocal;

  TithiDto({
    required this.name,
    required this.paksha,
    required this.endsAtLocal,
  });

  factory TithiDto.fromJson(Map<String, dynamic> json) {
    return TithiDto(
      name: json['name'] as String,
      paksha: json['paksha'] as String,
      endsAtLocal: json['ends_at_local'] as String,
    );
  }
}

class NakshatraDto {
  final String name;
  final String endsAtLocal;

  NakshatraDto({
    required this.name,
    required this.endsAtLocal,
  });

  factory NakshatraDto.fromJson(Map<String, dynamic> json) {
    return NakshatraDto(
      name: json['name'] as String,
      endsAtLocal: json['ends_at_local'] as String,
    );
  }
}

class MasaDto {
  final int index;
  final String name;

  MasaDto({required this.index, required this.name});

  factory MasaDto.fromJson(Map<String, dynamic> json) {
    return MasaDto(
      index: json['index'] as int,
      name: json['name'] as String,
    );
  }
}

class SunMoonDto {
  final String? sunriseLocal;
  final String? sunsetLocal;

  SunMoonDto({
    required this.sunriseLocal,
    required this.sunsetLocal,
  });

  factory SunMoonDto.fromJson(Map<String, dynamic> json) {
    return SunMoonDto(
      sunriseLocal: json['sunrise_local'] as String?,
      sunsetLocal: json['sunset_local'] as String?,
    );
  }
}

class MuhuratBundleDto {
  final String date;
  final List<MuhuratWindowDto> muhurats;

  MuhuratBundleDto({
    required this.date,
    required this.muhurats,
  });

  factory MuhuratBundleDto.fromJson(Map<String, dynamic> json) {
    return MuhuratBundleDto(
      date: json['date'] as String? ?? '',
      muhurats: (json['muhurtas'] as List<dynamic>? ?? [])
          .map((item) => MuhuratWindowDto.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class MuhuratWindowDto {
  final String id;
  final String name;
  final String sanskritName;
  final String devanagari;
  final String category;
  final String period;
  final String start;
  final String end;

  MuhuratWindowDto({
    required this.id,
    required this.name,
    required this.sanskritName,
    required this.devanagari,
    required this.category,
    required this.period,
    required this.start,
    required this.end,
  });

  factory MuhuratWindowDto.fromJson(Map<String, dynamic> json) {
    return MuhuratWindowDto(
      id: json['id'] as String,
      name: json['name'] as String,
      sanskritName: json['sanskrit_name'] as String? ?? '',
      devanagari: json['sanskrit_devanagari'] as String? ?? '',
      category: json['category'] as String? ?? '',
      period: json['period'] as String? ?? '',
      start: json['start'] as String,
      end: json['end'] as String,
    );
  }
}

class MuhuratDetailDto extends MuhuratWindowDto {
  final String? description;

  MuhuratDetailDto({
    required super.id,
    required super.name,
    required super.sanskritName,
    required super.devanagari,
    required super.category,
    required super.period,
    required super.start,
    required super.end,
    this.description,
  });

  factory MuhuratDetailDto.fromJson(Map<String, dynamic> json) {
    return MuhuratDetailDto(
      id: json['id'] as String,
      name: json['name'] as String,
      sanskritName: json['sanskrit_name'] as String? ?? '',
      devanagari: json['sanskrit_devanagari'] as String? ?? '',
      category: json['category'] as String? ?? '',
      period: json['period'] as String? ?? '',
      start: json['start'] as String,
      end: json['end'] as String,
      description: json['description'] as String?,
    );
  }
}

class FestivalTodayDto {
  final String? id;
  final String name;
  final String? type;

  FestivalTodayDto({
    required this.id,
    required this.name,
    required this.type,
  });

  factory FestivalTodayDto.fromJson(Map<String, dynamic> json) {
    return FestivalTodayDto(
      id: json['id'] as String?,
      name: json['name'] as String,
      type: json['type'] as String?,
    );
  }
}

class FestivalsTodayResponseDto {
  final List<FestivalTodayDto> festivals;

  FestivalsTodayResponseDto({required this.festivals});

  factory FestivalsTodayResponseDto.fromJson(Map<String, dynamic> json) {
    final items = (json['festivals'] as List<dynamic>? ?? [])
        .map((item) => FestivalTodayDto.fromJson(item as Map<String, dynamic>))
        .toList();
    return FestivalsTodayResponseDto(festivals: items);
  }
}

class UpcomingFestivalDto {
  final String date;
  final String name;
  final String? weekday;
  final String? type;

  UpcomingFestivalDto({
    required this.date,
    required this.name,
    required this.weekday,
    required this.type,
  });

  factory UpcomingFestivalDto.fromJson(Map<String, dynamic> json) {
    return UpcomingFestivalDto(
      date: json['date'] as String,
      name: json['name'] as String,
      weekday: json['weekday'] as String?,
      type: json['type'] as String?,
    );
  }
}

class FestivalsUpcomingResponseDto {
  final List<UpcomingFestivalDto> items;

  FestivalsUpcomingResponseDto({required this.items});

  factory FestivalsUpcomingResponseDto.fromJson(Map<String, dynamic> json) {
    final items = (json['items'] as List<dynamic>? ?? [])
        .map((item) => UpcomingFestivalDto.fromJson(item as Map<String, dynamic>))
        .toList();
    return FestivalsUpcomingResponseDto(items: items);
  }
}

class FestivalContentDto {
  final String? name;
  final String? subtitle;
  final String? about;
  final String? significance;
  final String? history;
  final String? scriptures;
  final String? pujaVidhi;
  final String? sourceUrl;
  final String? scrapedAt;

  FestivalContentDto({
    required this.name,
    required this.subtitle,
    required this.about,
    required this.significance,
    required this.history,
    required this.scriptures,
    required this.pujaVidhi,
    required this.sourceUrl,
    required this.scrapedAt,
  });

  factory FestivalContentDto.fromJson(Map<String, dynamic> json) {
    return FestivalContentDto(
      name: json['name'] as String?,
      subtitle: json['subtitle'] as String?,
      about: json['about'] as String?,
      significance: json['significance'] as String?,
      history: json['history'] as String?,
      scriptures: json['scriptures'] as String?,
      pujaVidhi: json['puja_vidhi'] as String?,
      sourceUrl: json['source_url'] as String?,
      scrapedAt: json['scraped_at'] as String?,
    );
  }
}

class FestivalFaqDto {
  final String question;
  final String answer;

  FestivalFaqDto({required this.question, required this.answer});

  factory FestivalFaqDto.fromJson(Map<String, dynamic> json) {
    return FestivalFaqDto(
      question: json['question'] as String? ?? '',
      answer: json['answer'] as String? ?? '',
    );
  }
}

class FestivalCalendarEventDto {
  final String id;
  final String name;
  final String? type;
  final bool? primary;
  final FestivalContentDto? content;
  final List<String> rituals;
  final List<FestivalFaqDto> faqs;

  FestivalCalendarEventDto({
    required this.id,
    required this.name,
    required this.type,
    required this.primary,
    required this.content,
    required this.rituals,
    required this.faqs,
  });

  factory FestivalCalendarEventDto.fromJson(Map<String, dynamic> json) {
    final contentJson = json['content'] as Map<String, dynamic>?;
    final rituals = (json['rituals'] as List<dynamic>? ?? [])
        .map((item) => item.toString())
        .toList();
    final faqs = (json['faqs'] as List<dynamic>? ?? [])
        .map((item) => FestivalFaqDto.fromJson(item as Map<String, dynamic>))
        .toList();
    return FestivalCalendarEventDto(
      id: json['id'] as String,
      name: json['name'] as String,
      type: json['type'] as String?,
      primary: json['primary'] as bool?,
      content: contentJson == null ? null : FestivalContentDto.fromJson(contentJson),
      rituals: rituals,
      faqs: faqs,
    );
  }
}

class FestivalCalendarDayDto {
  final int day;
  final String weekday;
  final List<FestivalCalendarEventDto> events;

  FestivalCalendarDayDto({
    required this.day,
    required this.weekday,
    required this.events,
  });

  factory FestivalCalendarDayDto.fromJson(Map<String, dynamic> json) {
    final events = (json['events'] as List<dynamic>? ?? [])
        .map((item) => FestivalCalendarEventDto.fromJson(item as Map<String, dynamic>))
        .toList();
    return FestivalCalendarDayDto(
      day: json['day'] as int,
      weekday: json['weekday'] as String,
      events: events,
    );
  }
}

class FestivalCalendarResponseDto {
  final int year;
  final int month;
  final List<FestivalCalendarDayDto> days;

  FestivalCalendarResponseDto({
    required this.year,
    required this.month,
    required this.days,
  });

  factory FestivalCalendarResponseDto.fromJson(Map<String, dynamic> json) {
    final days = (json['days'] as List<dynamic>? ?? [])
        .map((item) => FestivalCalendarDayDto.fromJson(item as Map<String, dynamic>))
        .toList();
    return FestivalCalendarResponseDto(
      year: json['year'] as int,
      month: json['month'] as int,
      days: days,
    );
  }
}

class FestivalPujaMuhuratDto {
  final String id;
  final String name;
  final String start;
  final String end;
  final int durationMinutes;
  final String? description;

  FestivalPujaMuhuratDto({
    required this.id,
    required this.name,
    required this.start,
    required this.end,
    required this.durationMinutes,
    required this.description,
  });

  factory FestivalPujaMuhuratDto.fromJson(Map<String, dynamic> json) {
    return FestivalPujaMuhuratDto(
      id: json['id'] as String,
      name: json['name'] as String? ?? '',
      start: json['start'] as String? ?? '',
      end: json['end'] as String? ?? '',
      durationMinutes: json['duration_minutes'] as int? ?? 0,
      description: json['description'] as String?,
    );
  }
}

class FestivalDateOccurrenceDto {
  final String date;
  final String? weekday;
  final List<String> traditions;
  final String? adhikStatus;
  final String? kshayaLabel;
  final List<FestivalPujaMuhuratDto> pujaMuhurats;
  final bool? primary;

  FestivalDateOccurrenceDto({
    required this.date,
    required this.weekday,
    required this.traditions,
    required this.adhikStatus,
    required this.kshayaLabel,
    required this.pujaMuhurats,
    required this.primary,
  });

  factory FestivalDateOccurrenceDto.fromJson(Map<String, dynamic> json) {
    final traditions = (json['traditions'] as List<dynamic>? ?? [])
        .map((item) => item.toString())
        .toList();
    final muhurats = (json['puja_muhurats'] as List<dynamic>? ?? [])
        .map((item) => FestivalPujaMuhuratDto.fromJson(item as Map<String, dynamic>))
        .toList();
    return FestivalDateOccurrenceDto(
      date: json['date'] as String? ?? '',
      weekday: json['weekday'] as String?,
      traditions: traditions,
      adhikStatus: json['adhik_status'] as String?,
      kshayaLabel: json['kshaya_label'] as String?,
      pujaMuhurats: muhurats,
      primary: json['primary'] as bool?,
    );
  }
}

class FestivalVariantDatesDto {
  final String id;
  final String name;
  final int count;
  final List<String> scopeTraditions;
  final List<FestivalDateOccurrenceDto> dates;

  FestivalVariantDatesDto({
    required this.id,
    required this.name,
    required this.count,
    required this.scopeTraditions,
    required this.dates,
  });

  factory FestivalVariantDatesDto.fromJson(Map<String, dynamic> json) {
    final scope = (json['scope_traditions'] as List<dynamic>? ?? [])
        .map((item) => item.toString())
        .toList();
    final dates = (json['dates'] as List<dynamic>? ?? [])
        .map((item) => FestivalDateOccurrenceDto.fromJson(item as Map<String, dynamic>))
        .toList();
    return FestivalVariantDatesDto(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      count: json['count'] as int? ?? dates.length,
      scopeTraditions: scope,
      dates: dates,
    );
  }
}

class FestivalDatesResponseDto {
  final String festivalId;
  final int year;
  final bool includeChildren;
  final List<FestivalVariantDatesDto> variants;
  final int total;

  FestivalDatesResponseDto({
    required this.festivalId,
    required this.year,
    required this.includeChildren,
    required this.variants,
    required this.total,
  });

  factory FestivalDatesResponseDto.fromJson(Map<String, dynamic> json) {
    final variants = (json['variants'] as List<dynamic>? ?? [])
        .map((item) => FestivalVariantDatesDto.fromJson(item as Map<String, dynamic>))
        .toList();
    return FestivalDatesResponseDto(
      festivalId: json['festival_id'] as String? ?? '',
      year: json['year'] as int? ?? 0,
      includeChildren: json['include_children'] as bool? ?? false,
      variants: variants,
      total: json['total'] as int? ?? variants.length,
    );
  }
}

class PanchangDashboardVm {
  final String dateLabel;
  final String lunarLabel;
  final String festivalTitle;
  final String tithiLabel;
  final String nakshatraLabel;
  final String sunriseLabel;
  final String sunsetLabel;
  final List<PanchangMuhuratVm> auspiciousMuhurats;
  final List<PanchangMuhuratVm> inauspiciousMuhurats;
  final String rashifalSign;
  final String rashifalText;
  final String rashifalSymbol;
  final String upcomingDateLabel;
  final String upcomingName;

  PanchangDashboardVm({
    required this.dateLabel,
    required this.lunarLabel,
    required this.festivalTitle,
    required this.tithiLabel,
    required this.nakshatraLabel,
    required this.sunriseLabel,
    required this.sunsetLabel,
    required this.auspiciousMuhurats,
    required this.inauspiciousMuhurats,
    required this.rashifalSign,
    required this.rashifalText,
    required this.rashifalSymbol,
    required this.upcomingDateLabel,
    required this.upcomingName,
  });
}

class PanchangMuhuratVm {
  final String id;
  final String name;
  final String timeRange;
  final String sanskritName;
  final String devanagari;
  final String category; // 'auspicious' | 'inauspicious'
  final String period;   // 'day' | 'night'

  PanchangMuhuratVm({
    required this.id,
    required this.name,
    required this.timeRange,
    required this.sanskritName,
    required this.devanagari,
    required this.category,
    required this.period,
  });
}

class HoroscopeDailyDto {
  final String sign;
  final String? prediction;
  final String? dateLabel;
  final Map<String, dynamic>? ratings;

  HoroscopeDailyDto({
    required this.sign,
    required this.prediction,
    required this.dateLabel,
    required this.ratings,
  });

  factory HoroscopeDailyDto.fromJson(Map<String, dynamic> json) {
    return HoroscopeDailyDto(
      sign: json['sign'] as String? ?? '',
      prediction: json['prediction'] as String?,
      dateLabel: json['date_label'] as String?,
      ratings: json['ratings'] as Map<String, dynamic>?,
    );
  }
}
