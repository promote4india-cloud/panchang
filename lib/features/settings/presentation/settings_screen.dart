import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../config/user_config.dart';
import '../../../constants/app_colors.dart';
import '../../../constants/app_themes.dart';
import '../../../providers/user_location_provider.dart';

class SettingsView extends ConsumerStatefulWidget {
  const SettingsView({super.key});

  @override
  ConsumerState<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends ConsumerState<SettingsView> {
  // Local state properties managing interactive toggle switch targets
  bool _dailyRahuKaalReminder = true;
  bool _importantFestivalsReminder = false;

  @override
  Widget build(BuildContext context) {
    final locationState = ref.watch(userLocationProvider);
    final autoDetection = locationState.value?.automaticDetection ?? true;
    final isLocationBusy = locationState.isLoading;

    return SingleChildScrollView(
      // Clear bounds spacing allowance logic parameters for fixed bottom nav bar
      padding: const EdgeInsets.only(left: 16.0, right: 16.0, top: 24.0, bottom: 120.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // --- Profile Card Module ---
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: AppColors.primaryContainer.withOpacity(0.08),
                  blurRadius: 20,
                  offset: const Offset(0, 4),
                )
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 64,
                  height: 64,
                  decoration: const BoxDecoration(
                    color: AppColors.primaryContainer,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(LucideIcons.user, color: Colors.white, size: 32),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(UserConfig.name, style: AppThemes.headlineSm.copyWith(color: AppColors.onSurface)),
                      const SizedBox(height: 2),
                      Text('Vedic Practitioner since 2018', style: AppThemes.bodySm.copyWith(color: AppColors.onSurfaceVariant)),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(LucideIcons.edit2, color: AppColors.primaryContainer, size: 18),
                  onPressed: () {},
                )
              ],
            ),
          ),
          const SizedBox(height: 24),

          // --- SECTION: LOCATION SETTINGS ---
          _buildGroupHeader('Location'),
          const SizedBox(height: 8),
          Container(
            decoration: _groupContainerDecoration(),
            child: Column(
              children: [
                _buildToggleRow(
                  icon: LucideIcons.locate,
                  title: 'Automatic Detection',
                  subtitle: 'Uses GPS for precise Muhurta',
                  value: autoDetection,
                  onChanged: isLocationBusy ? null : (val) => _handleAutomaticDetectionChange(val),
                  showDivider: true,
                ),
                _buildNavigationRow(
                  icon: LucideIcons.map,
                  title: 'Manual Entry',
                  trailingText: 'Varanasi, India',
                  onTap: () {},
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // --- SECTION: REMINDERS SETTINGS ---
          _buildGroupHeader('Reminders'),
          const SizedBox(height: 8),
          Container(
            decoration: _groupContainerDecoration(),
            child: Column(
              children: [
                _buildToggleRow(
                  icon: LucideIcons.bell,
                  title: 'Daily Rahu Kaal',
                  subtitle: 'Alert 15 mins before start',
                  value: _dailyRahuKaalReminder,
                  onChanged: (val) => setState(() => _dailyRahuKaalReminder = val),
                  showDivider: true,
                ),
                _buildToggleRow(
                  icon: LucideIcons.calendar,
                  title: 'Important Festivals',
                  subtitle: 'Notifications for major tithis',
                  value: _importantFestivalsReminder,
                  onChanged: (val) => setState(() => _importantFestivalsReminder = val),
                  showDivider: false,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // --- SECTION: PREFERENCES ---
          _buildGroupHeader('Preferences'),
          const SizedBox(height: 8),
          Container(
            decoration: _groupContainerDecoration(),
            child: Column(
              children: [
                _buildNavigationRow(
                  icon: LucideIcons.languages,
                  title: 'Language',
                  trailingText: 'English',
                  showDivider: true,
                  onTap: () {},
                ),
                _buildNavigationRow(
                  icon: LucideIcons.moon,
                  title: 'Appearance',
                  trailingText: 'System Default',
                  onTap: () {},
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),

          // --- Footer Meta Info Section ---
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              GestureDetector(
                onTap: () {},
                child: Text('Privacy Policy', style: AppThemes.labelMd.copyWith(color: AppColors.primaryContainer)),
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 12.0),
                child: Text('•', style: TextStyle(color: AppColors.outlineVariant)),
              ),
              GestureDetector(
                onTap: () {},
                child: Text('Terms of Service', style: AppThemes.labelMd.copyWith(color: AppColors.primaryContainer)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Vedic Panchang v2.4.1 — Alignment with the Cosmos',
            textAlign: TextAlign.center,
            style: AppThemes.bodySm.copyWith(color: AppColors.onSurfaceVariant.withOpacity(0.6), fontSize: 12),
          ),
        ],
      ),
    );
  }

  // =========================================================================
  // HELPER SUB-COMPONENT WIDGET BUILDERS
  // =========================================================================

  Widget _buildGroupHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8.0), // Fixed here
      child: Text(
        title.toUpperCase(),
        style: AppThemes.labelLg.copyWith(
          color: AppColors.primaryContainer,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
      ),
    );
  }

  BoxDecoration _groupContainerDecoration() {
    return BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      boxShadow: [
        BoxShadow(
          color: AppColors.primaryContainer.withOpacity(0.04),
          blurRadius: 20,
          offset: const Offset(0, 4),
        )
      ],
    );
  }

  Widget _buildToggleRow({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool>? onChanged,
    bool showDivider = false,
  }) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
          child: Row(
            children: [
              Icon(icon, color: AppColors.onSurfaceVariant, size: 22),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppThemes.bodyLg.copyWith(fontWeight: FontWeight.w500, fontSize: 16)),
                    const SizedBox(height: 2),
                    Text(subtitle, style: AppThemes.bodySm.copyWith(color: AppColors.onSurfaceVariant)),
                  ],
                ),
              ),
              Switch.adaptive(
                value: value,
                onChanged: onChanged,
                activeColor: Colors.white,
                activeTrackColor: AppColors.primaryContainer,
                inactiveTrackColor: AppColors.outlineVariant.withOpacity(0.4),
              ),
            ],
          ),
        ),
        if (showDivider)
          Divider(color: AppColors.outlineVariant.withOpacity(0.3), height: 1, indent: 54),
      ],
    );
  }

  Widget _buildNavigationRow({
    required IconData icon,
    required String title,
    required String trailingText,
    required VoidCallback onTap,
    bool showDivider = false,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 16.0),
            child: Row(
              children: [
                Icon(icon, color: AppColors.onSurfaceVariant, size: 22),
                const SizedBox(width: 16),
                Expanded(
                  child: Text(
                    title, 
                    style: AppThemes.bodyLg.copyWith(fontWeight: FontWeight.w500, fontSize: 16)
                  ),
                ),
                Text(
                  trailingText, 
                  style: AppThemes.bodySm.copyWith(color: AppColors.onSurfaceVariant, fontWeight: FontWeight.w500)
                ),
                const SizedBox(width: 6),
                const Icon(LucideIcons.chevronRight, color: AppColors.outlineVariant, size: 18),
              ],
            ),
          ),
          if (showDivider)
            Divider(color: AppColors.outlineVariant.withOpacity(0.3), height: 1, indent: 54),
        ],
      ),
    );
  }

  Future<void> _handleAutomaticDetectionChange(bool enabled) async {
    await ref.read(userLocationProvider.notifier).setAutomaticDetection(enabled);
    if (!enabled) return;

    final permissionOk = await _ensureLocationPermission();
    if (!permissionOk) return;

    try {
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
      await ref.read(userLocationProvider.notifier).setCoordinates(
            position.latitude,
            position.longitude,
          );
    } catch (error) {
      _showSnack('Unable to fetch current location.');
    }
  }

  Future<bool> _ensureLocationPermission() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      _showSnack('Location services are disabled.');
      return false;
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
      _showSnack('Location permission denied.');
      return false;
    }

    return true;
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}