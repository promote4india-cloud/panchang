import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../config/user_config.dart';
import '../../../constants/app_colors.dart';
import '../../../constants/app_themes.dart';
import '../../../features/panchang/providers/panchang_providers.dart';
import '../../../models/location_models.dart';
import '../../../providers/app_providers.dart';
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
    final manualLocationLabel =
        locationState.value?.label ?? UserConfig.locationLabel;
    final selectedThemeMode = ref.watch(themeModeProvider);
    final appearanceLabel = _appearanceLabel(selectedThemeMode);
    final c = AppColorsOf(context);

    return SingleChildScrollView(
      // Clear bounds spacing allowance logic parameters for fixed bottom nav bar
      padding: EdgeInsets.only(
        left: 16.0,
        right: 16.0,
        top: 24.0,
        bottom: MediaQuery.of(context).padding.bottom + 12,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // --- Profile Card Module ---
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: c.card,
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: c.primaryContainer.withOpacity(0.08),
                  blurRadius: 20,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    color: c.primaryContainer,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    LucideIcons.user,
                    color: Colors.white,
                    size: 32,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        UserConfig.name,
                        style: AppThemes.headlineSm.copyWith(
                          color: c.onSurface,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Vedic Practitioner since 2018',
                        style: AppThemes.bodySm.copyWith(
                          color: c.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: Icon(
                    LucideIcons.edit2,
                    color: c.primaryContainer,
                    size: 18,
                  ),
                  onPressed: () {},
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // --- SECTION: LOCATION SETTINGS ---
          _buildGroupHeader(context, 'Location'),
          const SizedBox(height: 8),
          Container(
            decoration: _groupContainerDecoration(c),
            child: Column(
              children: [
                _buildToggleRow(
                  context,
                  icon: LucideIcons.locate,
                  title: 'Automatic Detection',
                  subtitle: 'Uses GPS for precise Muhurta',
                  value: autoDetection,
                  onChanged: isLocationBusy
                      ? null
                      : (val) => _handleAutomaticDetectionChange(val),
                  showDivider: true,
                ),
                _buildNavigationRow(
                  context,
                  icon: LucideIcons.map,
                  title: 'Manual Entry',
                  trailingText: _firstWord(manualLocationLabel),
                  onTap: _openManualLocationSearch,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // --- SECTION: REMINDERS SETTINGS ---
          _buildGroupHeader(context, 'Reminders'),
          const SizedBox(height: 8),
          Container(
            decoration: _groupContainerDecoration(c),
            child: Column(
              children: [
                _buildToggleRow(
                  context,
                  icon: LucideIcons.bell,
                  title: 'Daily Rahu Kaal',
                  subtitle: 'Alert 15 mins before start',
                  value: _dailyRahuKaalReminder,
                  onChanged: (val) =>
                      setState(() => _dailyRahuKaalReminder = val),
                  showDivider: true,
                ),
                _buildToggleRow(
                  context,
                  icon: LucideIcons.bell,
                  title: 'Important Festivals',
                  subtitle: 'Notifications for major tithis',
                  value: _importantFestivalsReminder,
                  onChanged: (val) =>
                      setState(() => _importantFestivalsReminder = val),
                  showDivider: false,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // --- SECTION: PREFERENCES ---
          _buildGroupHeader(context, 'Preferences'),
          const SizedBox(height: 8),
          Container(
            decoration: _groupContainerDecoration(c),
            child: Column(
              children: [
                _buildNavigationRow(
                  context,
                  icon: LucideIcons.languages,
                  title: 'Language',
                  trailingText: 'English',
                  showDivider: true,
                  onTap: () {},
                ),
                _buildNavigationRow(
                  context,
                  icon: LucideIcons.moon,
                  title: 'Appearance',
                  trailingText: appearanceLabel,
                  onTap: () => _showAppearanceDialog(),
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
                child: Text(
                  'Privacy Policy',
                  style: AppThemes.labelMd.copyWith(
                    color: c.primaryContainer,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12.0),
                child: Text(
                  '•',
                  style: TextStyle(color: c.outlineVariant),
                ),
              ),
              GestureDetector(
                onTap: () {},
                child: Text(
                  'Terms of Service',
                  style: AppThemes.labelMd.copyWith(
                    color: c.primaryContainer,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Vedic Panchang v2.4.1 — Alignment with the Cosmos',
            textAlign: TextAlign.center,
            style: AppThemes.bodySm.copyWith(
              color: c.onSurfaceVariant.withOpacity(0.6),
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  // =========================================================================
  // HELPER SUB-COMPONENT WIDGET BUILDERS
  // =========================================================================

  Widget _buildGroupHeader(BuildContext context, String title) {
    final c = AppColorsOf(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8.0), // Fixed here
      child: Text(
        title.toUpperCase(),
        style: AppThemes.labelLg.copyWith(
          color: c.primaryContainer,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
      ),
    );
  }

  BoxDecoration _groupContainerDecoration(AppColorsOf c) {
    return BoxDecoration(
      color: c.card,
      borderRadius: BorderRadius.circular(12),
      boxShadow: [
        BoxShadow(
          color: c.primaryContainer.withOpacity(0.04),
          blurRadius: 20,
          offset: const Offset(0, 4),
        ),
      ],
    );
  }

  String _appearanceLabel(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.dark:
        return 'Dark Mode';
      case ThemeMode.light:
        return 'Light Mode';
      case ThemeMode.system:
      default:
        return 'System Default';
    }
  }

  Future<void> _showAppearanceDialog() async {
    final currentMode = ref.read(themeModeProvider);
    ThemeMode selectedMode = currentMode;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('Appearance'),
              contentPadding: const EdgeInsets.fromLTRB(24, 12, 24, 0),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  RadioListTile<ThemeMode>(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Light Mode'),
                    value: ThemeMode.light,
                    groupValue: selectedMode,
                    onChanged: (value) {
                      if (value == null) return;
                      ref.read(themeModeProvider.notifier).setThemeMode(value);
                      Navigator.of(dialogContext).pop();
                    },
                  ),
                  RadioListTile<ThemeMode>(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Dark Mode'),
                    value: ThemeMode.dark,
                    groupValue: selectedMode,
                    onChanged: (value) {
                      if (value == null) return;
                      ref.read(themeModeProvider.notifier).setThemeMode(value);
                      Navigator.of(dialogContext).pop();
                    },
                  ),
                  RadioListTile<ThemeMode>(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('System Default'),
                    value: ThemeMode.system,
                    groupValue: selectedMode,
                    onChanged: (value) {
                      if (value == null) return;
                      ref.read(themeModeProvider.notifier).setThemeMode(value);
                      Navigator.of(dialogContext).pop();
                    },
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Widget _buildToggleRow(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool>? onChanged,
    bool showDivider = false,
  }) {
    final c = AppColorsOf(context);
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
          child: Row(
            children: [
              Icon(icon, color: c.onSurfaceVariant, size: 22),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: AppThemes.bodyLg.copyWith(
                        fontWeight: FontWeight.w500,
                        fontSize: 16,
                        color: c.onSurface,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: AppThemes.bodySm.copyWith(
                        color: c.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Switch.adaptive(
                value: value,
                onChanged: onChanged,
                activeColor: Colors.white,
                activeTrackColor: c.primaryContainer,
                inactiveTrackColor: c.outlineVariant.withOpacity(0.4),
              ),
            ],
          ),
        ),
        if (showDivider)
          Divider(
            color: c.outlineVariant.withOpacity(0.3),
            height: 1,
            indent: 54,
          ),
      ],
    );
  }

  Widget _buildNavigationRow(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String trailingText,
    required VoidCallback onTap,
    bool showDivider = false,
  }) {
    final c = AppColorsOf(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: 16.0,
              vertical: 16.0,
            ),
            child: Row(
              children: [
                Icon(icon, color: c.onSurfaceVariant, size: 22),
                const SizedBox(width: 16),
                Expanded(
                  child: Text(
                    title,
                    style: AppThemes.bodyLg.copyWith(
                      fontWeight: FontWeight.w500,
                      fontSize: 16,
                      color: c.onSurface,
                    ),
                  ),
                ),
                Text(
                  trailingText,
                  style: AppThemes.bodySm.copyWith(
                    color: c.onSurfaceVariant,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 6),
                Icon(
                  LucideIcons.chevronRight,
                  color: c.outlineVariant,
                  size: 18,
                ),
              ],
            ),
          ),
          if (showDivider)
            Divider(
              color: c.outlineVariant.withOpacity(0.3),
              height: 1,
              indent: 54,
            ),
        ],
      ),
    );
  }

  Future<void> _openManualLocationSearch() async {
    final controller = TextEditingController();
    final focusNode = FocusNode();
    Timer? debounce;
    var results = <LocationSearchResult>[];
    var isSearching = false;
    var query = '';

    Future<void> runSearch(String value, StateSetter setState) async {
      final trimmed = value.trim();
      query = trimmed;
      debounce?.cancel();
      if (trimmed.length < 3) {
        setState(() {
          results = [];
          isSearching = false;
        });
        return;
      }

      debounce = Timer(const Duration(milliseconds: 250), () async {
        setState(() => isSearching = true);
        try {
          final api = ref.read(panchangApiProvider);
          final items = await api.searchLocations(
            query: trimmed,
            country: 'IN',
            language: UserConfig.language,
            limit: 10,
          );
          if (!mounted) return;
          setState(() {
            results = items.where((item) => item.country == 'IN').toList();
            isSearching = false;
          });
        } catch (_) {
          if (!mounted) return;
          setState(() => isSearching = false);
          _showSnack('Unable to search locations.');
        }
      });
    }

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('Search Location'),
              content: SizedBox(
                width: double.maxFinite,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: controller,
                      focusNode: focusNode,
                      autofocus: true,
                      decoration: const InputDecoration(
                        hintText: 'Type at least 3 characters',
                        prefixIcon: Icon(LucideIcons.search, size: 18),
                      ),
                      onChanged: (value) => runSearch(value, setState),
                    ),
                    const SizedBox(height: 12),
                    if (isSearching)
                      const SizedBox(
                        height: 120,
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (query.length < 3)
                      const SizedBox(
                        height: 120,
                        child: Center(
                          child: Text('Enter 3 or more characters.'),
                        ),
                      )
                    else if (results.isEmpty)
                      const SizedBox(
                        height: 120,
                        child: Center(child: Text('No locations found.')),
                      )
                    else
                      SizedBox(
                        height: 280,
                        child: ListView.separated(
                          itemCount: results.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, index) {
                            final item = results[index];
                            return ListTile(
                              title: Text(item.displayLabel),
                              subtitle: Text(item.subtitleLabel()),
                              onTap: () async {
                                Navigator.of(dialogContext).pop();
                                await ref
                                    .read(userLocationProvider.notifier)
                                    .setManualLocation(
                                      latitude: item.lat,
                                      longitude: item.lon,
                                      label: item.displayLabel,
                                      timezone: item.tz,
                                    );
                              },
                            );
                          },
                        ),
                      ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Close'),
                ),
              ],
            );
          },
        );
      },
    );

    debounce?.cancel();
    controller.dispose();
    focusNode.dispose();
  }

  Future<void> _handleAutomaticDetectionChange(bool enabled) async {
    await ref
        .read(userLocationProvider.notifier)
        .setAutomaticDetection(enabled);
    if (!enabled) return;

    final permissionOk = await _ensureLocationPermission();
    if (!permissionOk) return;

    try {
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
      await ref
          .read(userLocationProvider.notifier)
          .setCoordinates(position.latitude, position.longitude);
    } catch (error) {
      _showSnack('Unable to fetch current location.');
    }
  }

  String _firstWord(String value) {
    final trimmed = value.trim();
    if (trimmed.isEmpty) return value;
    final parts = trimmed.split(RegExp(r'\s+'));
    return parts.isNotEmpty ? parts.first : value;
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

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      _showSnack('Location permission denied.');
      return false;
    }

    return true;
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }
}
