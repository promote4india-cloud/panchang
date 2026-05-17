import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../constants/app_colors.dart';
import '../../../constants/app_themes.dart';

class FestivalsView extends StatelessWidget {
  const FestivalsView({super.key});

  @override
  Widget build(BuildContext context) {
    // Dynamic breakpoint tracking
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth > 768;

    return SingleChildScrollView(
      padding: const EdgeInsets.only(left: 16.0, right: 16.0, top: 24.0, bottom: 120.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // --- Hero Month Header Section ---
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'MASA: KARTIKA',
                      style: AppThemes.labelMd.copyWith(
                        color: AppColors.primaryContainer, 
                        fontWeight: FontWeight.bold, 
                        letterSpacing: 1.5
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text('November 2024', style: AppThemes.headlineLgMobile.copyWith(fontSize: 24)),
                  ],
                ),
              ),
              // Month Selector Control Panel
              Container(
                padding: const EdgeInsets.all(2),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.03),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.outlineVariant.withOpacity(0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(LucideIcons.chevronLeft, size: 16),
                      onPressed: () {},
                      constraints: const BoxConstraints(),
                      padding: const EdgeInsets.all(4),
                    ),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 6.0),
                      child: Text('Select Month', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, fontFamily: 'Manrope')),
                    ),
                    IconButton(
                      icon: const Icon(LucideIcons.chevronRight, size: 16),
                      onPressed: () {},
                      constraints: const BoxConstraints(),
                      padding: const EdgeInsets.all(4),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // --- Calendar Layout Section Splits ---
          if (isDesktop)
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(flex: 7, child: _buildGridCalendarBlock(screenWidth)),
                const SizedBox(width: 24),
                Expanded(flex: 5, child: _buildSideEventsBarBlock()),
              ],
            )
          else
            Column(
              children: [
                _buildGridCalendarBlock(screenWidth),
                const SizedBox(height: 20),
                _buildSideEventsBarBlock(),
              ],
            ),
          const SizedBox(height: 24),

          // --- Fixed: Mobile Responsive List Alternative View to replace table ---
          Text('Full Calendar View', style: AppThemes.headlineMd.copyWith(color: AppColors.onSurface, fontSize: 20)),
          const SizedBox(height: 12),
          ListView(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            children: [
              _buildResponsiveCalendarRow('Nov 01, Fri', 'Amavasya, Krishna Paksha', 'Diwali, Lakshmi Puja', 'HIGH', Colors.green),
              _buildResponsiveCalendarRow('Nov 02, Sat', 'Pratipada, Shukla Paksha', 'Govardhan Puja, Annakut', 'HIGH', Colors.green),
              _buildResponsiveCalendarRow('Nov 03, Sun', 'Dwitiya, Shukla Paksha', 'Bhai Dooj', 'MODERATE', AppColors.primaryContainer),
              _buildResponsiveCalendarRow('Nov 07, Thu', 'Shashti, Shukla Paksha', 'Chhath Puja (Arghya)', 'HIGH', Colors.green),
            ],
          )
        ],
      ),
    );
  }

  // =========================================================================
  // SUB-LAYOUT MODULAR BUILDERS
  // =========================================================================

  Widget _buildGridCalendarBlock(double screenWidth) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.outlineVariant.withOpacity(0.3)),
        boxShadow: [BoxShadow(color: AppColors.primary.withOpacity(0.04), blurRadius: 20, offset: const Offset(0, 4))],
      ),
      child: Column(
        children: [
          // Seven Days Column Header Titles Label row
          Container(
            padding: const EdgeInsets.symmetric(vertical: 10),
            color: Colors.black.withOpacity(0.02),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: const [
                Expanded(child: Text('SUN', textAlign: TextAlign.center, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.onSurfaceVariant))),
                Expanded(child: Text('MON', textAlign: TextAlign.center, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.onSurfaceVariant))),
                Expanded(child: Text('TUE', textAlign: TextAlign.center, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.onSurfaceVariant))),
                Expanded(child: Text('WED', textAlign: TextAlign.center, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.onSurfaceVariant))),
                Expanded(child: Text('THU', textAlign: TextAlign.center, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.onSurfaceVariant))),
                Expanded(child: Text('FRI', textAlign: TextAlign.center, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.onSurfaceVariant))),
                Expanded(child: Text('SAT', textAlign: TextAlign.center, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.onSurfaceVariant))),
              ],
            ),
          ),
          // Grid Days Matrix
          GridView.count(
            crossAxisCount: 7,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            childAspectRatio: screenWidth > 400 ? 0.75 : 0.65, // Dynamically scales spacing based on device width
            children: [
              // Row 1: Placeholders
              _buildEmptyDayCell(), _buildEmptyDayCell(), _buildEmptyDayCell(), _buildEmptyDayCell(),
              _buildDayCell('1', tag: 'Diwali'),
              _buildDayCell('2'),
              _buildDayCell('3'),
              // Row 2
              _buildDayCell('4'),
              _buildDayCell('5'),
              _buildDayCell('6', tag: 'Chhath Puja', isHighlighted: true),
              _buildDayCell('7'),
              _buildDayCell('8'),
              _buildDayCell('9'),
              _buildDayCell('10'),
              // Row 3
              _buildDayCell('11'),
              _buildDayCell('12', tag: 'Devutthana..', isHighlighted: true),
              _buildDayCell('13'),
              _buildDayCell('14'),
              _buildDayCell('15'),
              _buildDayCell('16'),
              _buildDayCell('17'),
            ],
          )
        ],
      ),
    );
  }

  Widget _buildEmptyDayCell() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.01),
        border: Border.all(color: AppColors.outlineVariant.withOpacity(0.1)),
      ),
    );
  }

  Widget _buildDayCell(String day, {String? tag, bool isHighlighted = false}) {
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: isHighlighted ? AppColors.primaryContainer.withOpacity(0.05) : Colors.transparent,
        border: Border.all(color: AppColors.outlineVariant.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            day,
            style: TextStyle(
              fontWeight: isHighlighted ? FontWeight.bold : FontWeight.normal,
              color: isHighlighted ? AppColors.primaryContainer : AppColors.onSurface,
              fontSize: 12,
            ),
          ),
          if (tag != null)
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Container(width: 4, height: 4, decoration: const BoxDecoration(color: AppColors.primaryContainer, shape: BoxShape.circle)),
                  const SizedBox(height: 2),
                  WidthSizedBoxMax(
                    child: Text(
                      tag,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.bold, color: AppColors.primaryContainer),
                    ),
                  ),
                ],
              ),
            )
          else
            const SizedBox.shrink(),
        ],
      ),
    );
  }

  Widget _buildSideEventsBarBlock() {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.outlineVariant.withOpacity(0.3)),
            boxShadow: [BoxShadow(color: AppColors.primary.withOpacity(0.04), blurRadius: 20, offset: const Offset(0, 4))],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(LucideIcons.star, color: AppColors.primaryContainer, size: 20),
                  const SizedBox(width: 8),
                  Text('Featured Festivals', style: AppThemes.headlineMd.copyWith(color: AppColors.onSurface, fontSize: 18)),
                ],
              ),
              const SizedBox(height: 14),
              _buildFeaturedFestivalItem('Nov 01', 'Major Festival', 'Diwali', 'The festival of lights, celebrating the victory of light over darkness and the return of Lord Rama.'),
              const SizedBox(height: 12),
              _buildFeaturedFestivalItem('Nov 12', 'Vrat', 'Devutthana Ekadashi', 'Fasting for Lord Vishnu. Marks the end of the four-month Chaturmas period.'),
              const SizedBox(height: 12),
              _buildFeaturedFestivalItem('Nov 15', 'Full Moon', 'Kartik Purnima', 'A holy day for a ritual bath in sacred rivers. Also celebrated as Dev Deepawali in Varanasi.'),
            ],
          ),
        ),
        const SizedBox(height: 16),
        
        // Dynamic Card Graphic Module
        Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            boxShadow: [BoxShadow(color: AppColors.primaryContainer.withOpacity(0.15), blurRadius: 15, offset: const Offset(0, 4))],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Stack(
              children: [
                Positioned.fill(
                  child: Image.network(
                    'https://lh3.googleusercontent.com/aida-public/AB6AXuCFKZyD0LVQwZg86F_GVNdtk0xsue64DOzIzm9rJeYit6z3wd8F4_6khnlqcLl86D9rKDlNSpqs5n-wnW9dKfKC7yCQdoB5c4F23k3uHxrvnCAcn5Tkzxd17865_MDmeTbPvD8-UjWUoZEDxiu-YReq9thHypKbongmHvrdYB9e7rkKQBhf6_VVz3b5Eb6bx8aF4Aq4E3GALvIoDBXIL0WEYUulmNWqtXWFZfIQz6MF9rOQBPAU1gCmWJVOXZphhwISFXWVJ8EYoVs',
                    fit: BoxFit.cover,
                  ),
                ),
                Positioned.fill(child: Container(color: AppColors.primaryContainer.withOpacity(0.75))),
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: const [
                      Row(
                        children: [
                          Icon(LucideIcons.sparkles, color: Colors.white, size: 20),
                          SizedBox(width: 8),
                          Text('Spiritual Tip', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold, fontFamily: 'Epilogue')),
                        ],
                      ),
                      SizedBox(height: 6),
                      Text(
                        'Kartika is the most sacred month. Lighting a lamp (Diya) daily near a Tulsi plant brings immense spiritual merit and peace to the household.',
                        style: TextStyle(color: Colors.white, fontSize: 13, height: 1.3, fontFamily: 'Manrope'),
                      )
                    ],
                  ),
                )
              ],
            ),
          ),
        )
      ],
    );
  }

  Widget _buildFeaturedFestivalItem(String date, String statusLabel, String title, String description) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: const Border(left: BorderSide(color: AppColors.primaryContainer, width: 4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(date, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.primaryContainer, fontFamily: 'Manrope')),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: AppColors.primaryContainer.withOpacity(0.1), borderRadius: BorderRadius.circular(100)),
                child: Text(statusLabel.toUpperCase(), style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppColors.primaryContainer)),
              )
            ],
          ),
          const SizedBox(height: 6),
          Text(title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.onSurface, fontFamily: 'Manrope')),
          const SizedBox(height: 4),
          Text(description, style: const TextStyle(fontSize: 12, color: AppColors.onSurfaceVariant, height: 1.4, fontFamily: 'Manrope')),
        ],
      ),
    );
  }

  // Custom adaptive component built to look clean on compact viewport sizes
  Widget _buildResponsiveCalendarRow(String date, String paksha, String festival, String urgency, Color highlightColor) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.outlineVariant.withOpacity(0.2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            flex: 3,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(date, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppColors.onSurface)),
                const SizedBox(height: 2),
                Text(paksha, style: const TextStyle(color: AppColors.onSurfaceVariant, fontSize: 11)),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            flex: 4,
            child: Text(
              festival, 
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppColors.onSurface)
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: highlightColor.withOpacity(0.1), borderRadius: BorderRadius.circular(100)),
            child: Text(urgency, style: TextStyle(color: highlightColor, fontSize: 9, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }
}

// Micro-helper container used to enforce hard truncation bounds
class WidthSizedBoxMax extends StatelessWidget {
  final Widget child;
  const WidthSizedBoxMax({required this.child, super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(width: double.infinity, child: child);
  }
}