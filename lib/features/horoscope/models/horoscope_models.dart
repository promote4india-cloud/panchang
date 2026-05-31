class HoroscopePredictionDto {
  final String sign;
  final String period;
  final String? dateLabel;
  final String? prediction;
  final Map<String, dynamic>? categories;
  final String? advice;
  final Map<String, dynamic>? ratings;

  HoroscopePredictionDto({
    required this.sign,
    required this.period,
    required this.dateLabel,
    required this.prediction,
    required this.categories,
    required this.advice,
    required this.ratings,
  });

  factory HoroscopePredictionDto.fromJson(Map<String, dynamic> json) {
    return HoroscopePredictionDto(
      sign: json['sign'] as String? ?? '',
      period: json['period'] as String? ?? '',
      dateLabel: json['date_label'] as String?,
      prediction: json['prediction'] as String?,
      categories: json['categories'] as Map<String, dynamic>?,
      advice: json['advice'] as String?,
      ratings: json['ratings'] as Map<String, dynamic>?,
    );
  }
}
