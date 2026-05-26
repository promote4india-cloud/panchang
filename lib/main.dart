import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:panchang_app/constants/app_themes.dart';
import 'package:panchang_app/features/festivals/presentation/festivals_screen.dart';
import 'package:panchang_app/features/settings/presentation/settings_screen.dart';
import 'config/user_config_dev.dart';

// Import features via relative file mapping links
import 'constants/app_colors.dart';
import 'providers/app_providers.dart';
import 'features/panchang/presentation/panchang_dashboard_view.dart';
import 'features/horoscope/presentation/horoscope_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await UserConfigDevHelper.loadOverrides();
  runApp(
    const ProviderScope(child: VedicPanchangApp()),
  );
}

class VedicPanchangApp extends StatelessWidget {
  const VedicPanchangApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Vedic Panchang',
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: AppColors.surface,
        fontFamily: 'Manrope',
      ),
      home: const DashboardPage(),
    );
  }
}

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activeTabIndex = ref.watch(navigationProvider);
    // Watched top bar data changes
    final topBarState = ref.watch(topBarProvider);
    final appBarTitle = _titleForTab(activeTabIndex);

    final List<Widget> screens = [
      const PanchangDashboardView(), 
      const HoroscopeView(),         
      const FestivalsView(),
      const SettingsView(),
    ];

    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        leading: IconButton(
          icon: const Icon(LucideIcons.menu, color: AppColors.primaryContainer), 
          onPressed: () => ref.read(topBarProvider.notifier).handleMenuPressed(context),
        ),
        title: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              appBarTitle,
              style: AppThemes.headlineSm.copyWith(color: AppColors.primary),
            ),
            // if (topBarState.currentRegion != 'Detecting...')
            //   Text(
            //     topBarState.currentRegion,
            //     style: const TextStyle(fontSize: 11, color: AppColors.onSurfaceVariant, fontWeight: FontWeight.w500),
            //   ),
          ],
        ),
        centerTitle: true,
        actions: [
          // Dynamic Language Selection Toggle Button Context
          TextButton.icon(
            style: TextButton.styleFrom(foregroundColor: AppColors.primaryContainer),
            onPressed: () => ref.read(topBarProvider.notifier).handleLanguagePressed(),
            icon: const Icon(LucideIcons.languages, size: 18),
            label: Text(
              topBarState.selectedLanguage == 'English' ? 'EN' : 'HI',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            ),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1.0),
          child: Container(color: Colors.black.withOpacity(0.05), height: 1.0),
        ),
      ),
      body: Stack(
        children: [
          // Background Mandala Effect Vector Image Wrap
          Positioned.fill(
            child: Opacity(
              opacity: 0.03,
              child: Image.network(
                'https://lh3.googleusercontent.com/aida-public/AB6AXuCT3mdlgJrg8ueB6Xu0OVvkQ71-EvRttjGWMPpJv1HBfHcnpKFZh8HMvPrGC6yCajr2m7Wd0RQHxL5lw3fE5i2oDNvTQnUps9FPwKGbD8AwTrj0FNEtcKgJGM2BfqgDT-NPaVcAozBQh6zbv_ZUa8-wtTsKn30GtXYfg8M9_DkWwhk2XP0U-ws-lPSYcWDV6TrQ-CsIMBu7nalsa5IXjFeK0mX5tk_6Mw_kLqMw2-QUBPZ6n4MLsSvR9FouLPRH776fPF_kC6HNYMw',
                fit: BoxFit.cover,
              ),
            ),
          ),

          screens[activeTabIndex],

          // Bottom Navigation Dock View Bar Layout Setup
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: const BorderRadius.only(topLeft: Radius.circular(16), topRight: Radius.circular(16)),
                border: Border(top: BorderSide(color: AppColors.outlineVariant.withOpacity(0.5))),
                boxShadow: [BoxShadow(color: AppColors.primary.withOpacity(0.1), blurRadius: 20, offset: const Offset(0, -4))],
              ),
              child: SafeArea(
                top: false,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildInteractiveNavItem(ref, activeTabIndex, 0, LucideIcons.sparkles, 'Panchang'),
                    _buildInteractiveNavItem(ref, activeTabIndex, 1, LucideIcons.star, 'Horoscope'),
                    _buildInteractiveNavItem(ref, activeTabIndex, 2, LucideIcons.calendar, 'Festivals'),
                    _buildInteractiveNavItem(ref, activeTabIndex, 3, LucideIcons.settings, 'Settings'),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInteractiveNavItem(WidgetRef ref, int activeIndex, int index, IconData icon, String label) {
    final bool isActive = activeIndex == index;

    if (isActive) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.primaryContainer,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [BoxShadow(color: AppColors.primaryContainer.withOpacity(0.3), blurRadius: 10, offset: const Offset(0, 4))],
        ),
        child: Row(
          children: [
            Icon(icon, color: Colors.white, size: 20),
            const SizedBox(width: 6),
            Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
          ],
        ),
      );
    } else {
      return InkWell(
        onTap: () => ref.read(navigationProvider.notifier).changeTab(index),
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: AppColors.onSurfaceVariant, size: 22),
              const SizedBox(height: 2),
              Text(label, style: const TextStyle(color: AppColors.onSurfaceVariant, fontSize: 12, fontWeight: FontWeight.w500)),
            ],
          ),
        ),
      );
    }
  }

  String _titleForTab(int index) {
    switch (index) {
      case 1:
        return 'Horoscope';
      case 2:
        return 'Festivals';
      case 3:
        return 'Settings';
      case 0:
      default:
        return 'Vedic Panchang';
    }
  }
}