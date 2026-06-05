import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

class ZodiacIconItem {
  final String id;
  final String label;
  final String symbol;
  final IconData icon;

  const ZodiacIconItem({
    required this.id,
    required this.label,
    required this.symbol,
    required this.icon,
  });
}

const List<ZodiacIconItem> zodiacIconItems = [
  ZodiacIconItem(id: 'aries', label: 'Aries', symbol: '♈', icon: LucideIcons.sun),
  ZodiacIconItem(id: 'taurus', label: 'Taurus', symbol: '♉', icon: LucideIcons.trees),
  ZodiacIconItem(id: 'gemini', label: 'Gemini', symbol: '♊', icon: LucideIcons.users),
  ZodiacIconItem(id: 'cancer', label: 'Cancer', symbol: '♋', icon: LucideIcons.waves),
  ZodiacIconItem(id: 'leo', label: 'Leo', symbol: '♌', icon: LucideIcons.star),
  ZodiacIconItem(id: 'virgo', label: 'Virgo', symbol: '♍', icon: LucideIcons.sparkles),
  ZodiacIconItem(id: 'libra', label: 'Libra', symbol: '♎', icon: LucideIcons.moon),
  ZodiacIconItem(id: 'scorpio', label: 'Scorpio', symbol: '♏', icon: LucideIcons.star),
  ZodiacIconItem(id: 'sagittarius', label: 'Sagittarius', symbol: '♐', icon: LucideIcons.sun),
  ZodiacIconItem(id: 'capricorn', label: 'Capricorn', symbol: '♑', icon: LucideIcons.trees),
  ZodiacIconItem(id: 'aquarius', label: 'Aquarius', symbol: '♒', icon: LucideIcons.waves),
  ZodiacIconItem(id: 'pisces', label: 'Pisces', symbol: '♓', icon: LucideIcons.moon),
];

ZodiacIconItem? zodiacItemFor(String value) {
  final normalized = value.trim().toLowerCase();
  for (final item in zodiacIconItems) {
    if (item.id == normalized || item.label.toLowerCase() == normalized) {
      return item;
    }
  }
  return null;
}

String zodiacLabelFor(String value) {
  final item = zodiacItemFor(value);
  if (item != null) return item.label;
  if (value.isEmpty) return '';
  final normalized = value.toLowerCase();
  return normalized[0].toUpperCase() + normalized.substring(1);
}

String zodiacSymbolFor(String value) {
  final item = zodiacItemFor(value);
  return item?.symbol ?? '';
}

IconData zodiacIconFor(String value) {
  final item = zodiacItemFor(value);
  return item?.icon ?? LucideIcons.star;
}
