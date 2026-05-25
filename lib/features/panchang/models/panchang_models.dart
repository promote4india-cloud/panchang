class PanchangTodayDto {
  final String date;
  final String weekday;
  final TithiDto tithi;
  final NakshatraDto nakshatra;
  final MasaDto masa;
  final SunMoonDto sunMoon;

  PanchangTodayDto({
    required this.date,
    required this.weekday,
    required this.tithi,
    required this.nakshatra,
    required this.masa,
    required this.sunMoon,
  });

  factory PanchangTodayDto.fromJson(Map<String, dynamic> json) {
    return PanchangTodayDto(
      date: json['date'] as String,
      weekday: json['weekday'] as String,
      tithi: TithiDto.fromJson(json['tithi'] as Map<String, dynamic>),
      nakshatra: NakshatraDto.fromJson(json['nakshatra'] as Map<String, dynamic>),
      masa: MasaDto.fromJson(json['masa'] as Map<String, dynamic>),
      sunMoon: SunMoonDto.fromJson(json['sun_moon'] as Map<String, dynamic>),
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
  final String category;
  final String period;
  final String start;
  final String end;

  MuhuratWindowDto({
    required this.id,
    required this.name,
    required this.category,
    required this.period,
    required this.start,
    required this.end,
  });

  factory MuhuratWindowDto.fromJson(Map<String, dynamic> json) {
    return MuhuratWindowDto(
      id: json['id'] as String,
      name: json['name'] as String,
      category: json['category'] as String? ?? '',
      period: json['period'] as String? ?? '',
      start: json['start'] as String,
      end: json['end'] as String,
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
  final String name;
  final String timeRange;

  PanchangMuhuratVm({required this.name, required this.timeRange});
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
