import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
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
    return Consumer(
      builder: (context, ref, _) {
        final themeMode = ref.watch(themeModeProvider);

        return MaterialApp(
          debugShowCheckedModeBanner: false,
          title: 'Vedic Panchang',
          themeMode: themeMode,
          theme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.light,
            scaffoldBackgroundColor: AppColors.surface,
            fontFamily: 'Manrope',
            colorScheme: ColorScheme.fromSeed(
              seedColor: AppColors.primaryContainer,
              brightness: Brightness.light,
            ),
          ),
          darkTheme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.dark,
            scaffoldBackgroundColor: AppColors.surfaceDark,
            fontFamily: 'Manrope',
            colorScheme: ColorScheme.fromSeed(
              seedColor: AppColors.primaryContainer,
              brightness: Brightness.dark,
            ),
          ),
          home: const DashboardPage(),
        );
      },
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

    final c = AppColorsOf(context);
    final isDark = c.isDark;

    return Scaffold(
      appBar: AppBar(
        backgroundColor: isDark ? const Color(0xFF181818) : AppColors.surface,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        leading: IconButton(
          icon: Icon(LucideIcons.menu, color: c.primaryContainer), 
          onPressed: () => ref.read(topBarProvider.notifier).handleMenuPressed(context),
        ),
        title: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              appBarTitle,
              style: AppThemes.headlineSm.copyWith(color: c.primary),
            ),
          ],
        ),
        centerTitle: true,
        actions: [
          // Dynamic Language Selection Toggle Button Context
          TextButton.icon(
            style: TextButton.styleFrom(foregroundColor: c.primaryContainer),
            onPressed: () => ref.read(topBarProvider.notifier).handleLanguagePressed(),
            icon: Icon(LucideIcons.languages, size: 18, color: c.primaryContainer),
            label: Text(
              topBarState.selectedLanguage == 'English' ? 'EN' : 'HI',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: c.primaryContainer),
            ),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1.0),
          child: Container(
            color: isDark ? Colors.white.withOpacity(0.05) : Colors.black.withOpacity(0.05),
            height: 1.0,
          ),
        ),
      ),
      body: Stack(
        children: [
          // Animated transition when switching tabs
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 300),
            switchInCurve: Curves.easeInOut,
            switchOutCurve: Curves.easeInOut,
            transitionBuilder: (Widget child, Animation<double> animation) {
              final curved = CurvedAnimation(parent: animation, curve: Curves.easeInOut);
              return SlideTransition(
                position: Tween<Offset>(begin: const Offset(0.0, 0.06), end: Offset.zero).animate(curved),
                child: FadeTransition(opacity: curved, child: child),
              );
            },
            child: KeyedSubtree(
              key: ValueKey<int>(activeTabIndex),
              child: screens[activeTabIndex],
            ),
          ),
        ],
      ),
      bottomNavigationBar: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1B1B1B) : Colors.white,
          borderRadius: const BorderRadius.only(topLeft: Radius.circular(16), topRight: Radius.circular(16)),
          border: Border(top: BorderSide(color: (isDark ? Colors.white : AppColors.outlineVariant).withOpacity(0.16))),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(isDark ? 0.35 : 0.1), blurRadius: 20, offset: const Offset(0, -4))],
        ),
        child: SafeArea(
          top: false,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildInteractiveNavItem(context, ref, activeTabIndex, 0, LucideIcons.sparkles, 'Panchang'),
              _buildInteractiveNavItem(context, ref, activeTabIndex, 1, LucideIcons.star, 'Horoscope'),
              _buildInteractiveNavItem(context, ref, activeTabIndex, 2, LucideIcons.calendar, 'Festivals'),
              _buildInteractiveNavItem(context, ref, activeTabIndex, 3, LucideIcons.settings, 'Settings'),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInteractiveNavItem(BuildContext context, WidgetRef ref, int activeIndex, int index, IconData icon, String label) {
    final bool isActive = activeIndex == index;
    final c = AppColorsOf(context);

    // Fixed inner height so the nav bar never resizes during transitions.
    // Inactive Column: icon(22) + gap(2) + text(~17) ≈ 41 → use 46 for
    // comfortable breathing room on both layouts.
    const double itemHeight = 46;

    return InkWell(
      onTap: () => ref.read(navigationProvider.notifier).changeTab(index),
      borderRadius: BorderRadius.circular(12),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
        height: itemHeight,
        padding: EdgeInsets.symmetric(horizontal: isActive ? 12 : 8),
        decoration: BoxDecoration(
          color: isActive ? c.primaryContainer : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          boxShadow: isActive
              ? [BoxShadow(color: c.primaryContainer.withOpacity(0.28), blurRadius: 10, offset: const Offset(0, 4))]
              : [],
        ),
        child: ClipRect(
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 200),
            switchInCurve: Curves.easeInOut,
            switchOutCurve: Curves.easeInOut,
            transitionBuilder: (child, animation) =>
                FadeTransition(opacity: animation, child: child),
            child: isActive
                ? Row(
                    key: ValueKey('nav_active_$index'),
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(icon, color: Colors.white, size: 18),
                      const SizedBox(width: 6),
                      Flexible(
                        child: Text(
                          label,
                          overflow: TextOverflow.ellipsis,
                          maxLines: 1,
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                      ),
                    ],
                  )
                : Column(
                    key: ValueKey('nav_inactive_$index'),
                    mainAxisSize: MainAxisSize.min,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(icon, color: c.onSurfaceVariant, size: 22),
                      const SizedBox(height: 2),
                      Text(label, style: TextStyle(color: c.onSurfaceVariant, fontSize: 11, fontWeight: FontWeight.w500)),
                    ],
                  ),
          ),
        ),
      ),
    );
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