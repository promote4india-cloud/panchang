import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../../../constants/app_colors.dart';
import '../../../constants/app_themes.dart';
import '../../../assset/zodiac_icons.dart';
import '../models/panchang_models.dart';
import '../providers/panchang_providers.dart';
import '../../../providers/app_providers.dart';
import '../../../features/festivals/providers/festivals_providers.dart';

class PanchangDashboardView extends ConsumerWidget {
	const PanchangDashboardView({super.key});

	@override
	Widget build(BuildContext context, WidgetRef ref) {
		final dashboard = ref.watch(panchangDashboardProvider);
		final spiritualTip = ref.watch(spiritualTipProvider);

		return dashboard.when(
			data: (vm) => SingleChildScrollView(
				padding: EdgeInsets.only(
					left: 16,
					right: 16,
					top: 20,
					bottom: MediaQuery.of(context).viewPadding.bottom + 20,
				),
				child: Column(
					crossAxisAlignment: CrossAxisAlignment.stretch,
					children: [
						Center(
							child: Column(
								children: [
									Text(
										vm.dateLabel,
										style: AppThemes.bodyMd.copyWith(
											fontWeight: FontWeight.w600,
											color: AppColorsOf(context).onSurface,
										),
									),
									const SizedBox(height: 6),
									Text(
										vm.lunarLabel,
										style: AppThemes.bodyMd.copyWith(
											fontWeight: FontWeight.bold,
											color: AppColorsOf(context).primary,
										),
									),
								],
							),
						),
						if (vm.festivalTitle.trim().isEmpty)
							const SizedBox(height: 12),
						if (vm.festivalTitle.trim().isNotEmpty) ...[
							const SizedBox(height: 16),
							_FestivalCard(title: vm.festivalTitle),
							const SizedBox(height: 16),
						],
						Row(
							children: [
								Expanded(
									child: _InfoTile(
										title: 'Tithi',
										value: vm.tithiLabel,
										icon: LucideIcons.moon,
									),
								),
								const SizedBox(width: 12),
								Expanded(
									child: _InfoTile(
										title: 'Sunrise',
										value: vm.sunriseLabel,
										icon: LucideIcons.sun,
									),
								),
							],
						),
						const SizedBox(height: 12),
						Row(
							children: [
								Expanded(
									child: _InfoTile(
										title: 'Nakshatra',
										value: vm.nakshatraLabel,
										icon: LucideIcons.sparkles,
									),
								),
								const SizedBox(width: 12),
								Expanded(
									child: _InfoTile(
										title: 'Sunset',
										value: vm.sunsetLabel,
										icon: LucideIcons.moon,
									),
								),
							],
						),
						const SizedBox(height: 20),
						Text(
							'Muhurat Timings',
							style: AppThemes.headlineSm.copyWith(
								color: AppColorsOf(context).onSurface,
							),
						),
						const SizedBox(height: 10),
						_MuhuratScroller(
							title: 'Auspicious',
							items: vm.auspiciousMuhurats,
							isPositive: true,
						),
						const SizedBox(height: 12),
						_MuhuratScroller(
							title: 'Inauspicious',
							items: vm.inauspiciousMuhurats,
							isPositive: false,
						),
						const SizedBox(height: 22),
						_SectionHeader(
							title: 'Daily Rashifal',
							actionText: 'View All',
							onActionTap: () => ref.read(navigationProvider.notifier).changeTab(1),
						),
						const SizedBox(height: 10),
						_RashifalCard(
							sign: vm.rashifalSign,
							text: vm.rashifalText,
							symbol: vm.rashifalSymbol,
						),
						const SizedBox(height: 22),
						_SectionHeader(title: 'Upcoming Events'),
						const SizedBox(height: 10),
						_UpcomingEventCard(
							dateLabel: vm.upcomingDateLabel,
							name: vm.upcomingName,
							cta: 'Set Reminder',
						),
						const SizedBox(height: 18),
						_SpiritualTipCard(spiritualTip: spiritualTip),
					],
				),
			),
			loading: () => Center(
				child: CircularProgressIndicator(color: AppColorsOf(context).primary),
			),
			error: (error, stackTrace) => _ErrorState(
				message: error.toString(),
				onRetry: () => ref.refresh(panchangDashboardProvider),
			),
		);
	}
}

class _FestivalCard extends StatelessWidget {
	final String title;

	const _FestivalCard({required this.title});

	@override
	Widget build(BuildContext context) {
		final c = AppColorsOf(context);
		return Container(
			padding: const EdgeInsets.all(14),
			decoration: BoxDecoration(
				color: c.primaryContainer.withOpacity(0.08),
				borderRadius: BorderRadius.circular(16),
				border: Border.all(color: c.primaryContainer.withOpacity(0.2)),
			),
			child: Row(
				children: [
					Container(
						width: 44,
						height: 44,
						decoration: BoxDecoration(
							color: c.primaryContainer,
							shape: BoxShape.circle,
						),
						child: const Icon(LucideIcons.home, color: Colors.white),
					),
					const SizedBox(width: 12),
					Expanded(
						child: Column(
							crossAxisAlignment: CrossAxisAlignment.start,
							children: [
								Text(
									'Festival Today',
									style: AppThemes.bodySm.copyWith(color: c.onSurfaceVariant),
								),
								const SizedBox(height: 4),
								Text(
									title,
									style: AppThemes.bodyMd.copyWith(
										fontWeight: FontWeight.bold,
										color: c.onSurface,
									),
								),
							],
						),
					),
					Icon(LucideIcons.chevronRight, color: c.primaryContainer),
				],
			),
		);
	}
}

class _InfoTile extends StatelessWidget {
	final String title;
	final String value;
	final IconData icon;

	const _InfoTile({
		required this.title,
		required this.value,
		required this.icon,
	});

	@override
	Widget build(BuildContext context) {
		final c = AppColorsOf(context);
		return Container(
			padding: const EdgeInsets.all(12),
			decoration: BoxDecoration(
				color: c.card,
				borderRadius: BorderRadius.circular(12),
				border: Border.all(color: c.border),
			),
			child: Column(
				crossAxisAlignment: CrossAxisAlignment.start,
				children: [
					Row(
						children: [
							Icon(icon, size: 16, color: c.primaryContainer),
							const SizedBox(width: 6),
							Text(
								title,
								style: AppThemes.labelMd.copyWith(color: c.onSurfaceVariant),
							),
						],
					),
					const SizedBox(height: 8),
					Text(
						value,
						style: AppThemes.bodyMd.copyWith(
							fontWeight: FontWeight.bold,
							color: c.onSurface,
						),
					),
				],
			),
		);
	}
}

class _SectionHeader extends StatelessWidget {
	final String title;
	final String? pillText;
	final String? actionText;
	final VoidCallback? onActionTap;

	const _SectionHeader({
		required this.title,
		this.pillText,
		this.actionText,
		this.onActionTap,
	});

	@override
	Widget build(BuildContext context) {
		final c = AppColorsOf(context);
		return Row(
			children: [
				Expanded(
					child: Text(
						title,
						style: AppThemes.headlineSm.copyWith(color: c.onSurface),
					),
				),
				if (pillText != null)
					Container(
						padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
						decoration: BoxDecoration(
							color: c.primaryContainer,
							borderRadius: BorderRadius.circular(999),
						),
						child: Text(
							pillText!,
							style: AppThemes.labelMd.copyWith(color: Colors.white),
						),
					),
				if (actionText != null)
					InkWell(
						onTap: onActionTap,
						borderRadius: BorderRadius.circular(6),
						child: Padding(
							padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
							child: Text(
								actionText!,
								style: AppThemes.labelMd.copyWith(
									color: c.primaryContainer,
								),
							),
						),
					),
			],
		);
	}
}

class _MuhuratScroller extends StatelessWidget {
	final String title;
	final List<PanchangMuhuratVm> items;
	final bool isPositive;

	const _MuhuratScroller({
		required this.title,
		required this.items,
		required this.isPositive,
	});

	@override
	Widget build(BuildContext context) {
		final c = AppColorsOf(context);
		final toneColor = isPositive ? c.primaryContainer : c.error;
		final bgColor = isPositive
				? (c.isDark ? const Color(0xFF1A2E1A) : Colors.green[50] ?? AppColors.primaryContainer.withOpacity(0.08))
				: (c.isDark ? const Color(0xFF2E1A1A) : AppColors.errorContainerBg);
		final edgeShadow = c.isDark
				? Colors.white.withOpacity(0.28)
				: Colors.black.withOpacity(0.32);

		return Column(
			crossAxisAlignment: CrossAxisAlignment.start,
			children: [
				Text(
					title,
					style: AppThemes.labelMd.copyWith(color: toneColor),
				),
				const SizedBox(height: 8),
				SizedBox(
					height: 88,
					child: Stack(
						children: [
							ListView.separated(
								scrollDirection: Axis.horizontal,
								itemCount: items.length,
								separatorBuilder: (_, __) => const SizedBox(width: 10),
								itemBuilder: (context, index) {
									final item = items[index];
									return Container(
										width: 170,
										padding: const EdgeInsets.all(12),
										decoration: BoxDecoration(
											color: bgColor,
											borderRadius: BorderRadius.circular(12),
										),
										child: Column(
											crossAxisAlignment: CrossAxisAlignment.start,
											mainAxisAlignment: MainAxisAlignment.spaceBetween,
											children: [
												Text(
													item.name,
													maxLines: 1,
													overflow: TextOverflow.ellipsis,
													style: AppThemes.labelMd.copyWith(
														fontWeight: FontWeight.w800,
														fontSize: 14,
														color: c.onSurfaceVariant,
													),
												),
												Text(
													item.timeRange,
													style: AppThemes.bodySm.copyWith(
														fontWeight: FontWeight.w400,
														color: c.onSurface,
													),
												),
											],
										),
									);
								},
							),
							Positioned(
								right: 0,
								top: 0,
								bottom: 0,
								child: IgnorePointer(
									child: Container(
										width: 18,
										decoration: BoxDecoration(
											gradient: LinearGradient(
												begin: Alignment.centerRight,
												end: Alignment.centerLeft,
												colors: [
													edgeShadow,
													edgeShadow.withOpacity(0.0),
												],
											),
										),
									),
								),
							),
							Positioned(
								right: 2,
								top: 0,
								bottom: 0,
								child: IgnorePointer(
									child: Center(
										child: Icon(
											Icons.chevron_right,
											color: edgeShadow.withOpacity(0.85),
											size: 16,
										),
									),
								),
							),
						],
					),
				),
			],
		);
	}
}

class _RashifalCard extends StatefulWidget {
	final String sign;
	final String text;
	final String symbol;

	const _RashifalCard({
		required this.sign,
		required this.text,
		required this.symbol,
	});

	@override
	State<_RashifalCard> createState() => _RashifalCardState();
}

class _RashifalCardState extends State<_RashifalCard> {
	bool _expanded = false;

	String _truncateWords(String value, int limit) {
		final trimmed = value.trim();
		if (trimmed.isEmpty) return trimmed;
		final words = trimmed.split(RegExp(r'\s+'));
		if (words.length <= limit) return trimmed;
		return '${words.take(limit).join(' ')}...';
	}

	@override
	Widget build(BuildContext context) {
		final c = AppColorsOf(context);
		final displayText = _expanded
				? widget.text
				: _truncateWords(widget.text, 20);
		final icon = zodiacIconFor(widget.sign);
		final showSymbol = widget.symbol.trim().isNotEmpty;

		return Container(
			decoration: BoxDecoration(
				color: c.card,
				borderRadius: BorderRadius.circular(16),
				border: Border.all(color: c.border),
			),
			child: InkWell(
				onTap: () => setState(() => _expanded = !_expanded),
				borderRadius: BorderRadius.circular(16),
				child: Padding(
					padding: const EdgeInsets.all(14),
					child: Row(
						crossAxisAlignment: CrossAxisAlignment.start,
						children: [
							Container(
								width: 30,
								height: 30,
								decoration: BoxDecoration(
									shape: BoxShape.circle,
									border: Border.all(color: c.primaryContainer.withOpacity(0.4)),
									color: c.primaryContainer.withOpacity(0.08),
								),
								child: Center(
									child: showSymbol
										? Text(
											widget.symbol,
											style: AppThemes.bodyMd.copyWith(
												fontWeight: FontWeight.bold,
												color: c.primaryContainer,
											),
										)
										: Icon(icon, color: c.primaryContainer),
								),
							),
							const SizedBox(width: 12),
							Expanded(
								child: Column(
									crossAxisAlignment: CrossAxisAlignment.start,
									children: [
										Text(
											widget.sign,
											style: AppThemes.bodyMd.copyWith(
												fontWeight: FontWeight.bold,
												color: c.onSurface,
											),
										),
										const SizedBox(height: 6),
										Text(
											displayText,
											style: AppThemes.bodySm.copyWith(color: c.onSurfaceVariant),
										),
									],
								),
							),
						],
					),
				),
			),
		);
	}
}

class _UpcomingEventCard extends StatelessWidget {
	final String dateLabel;
	final String name;
	final String cta;

	const _UpcomingEventCard({
		required this.dateLabel,
		required this.name,
		required this.cta,
	});

	@override
	Widget build(BuildContext context) {
		final c = AppColorsOf(context);
		return Container(
			padding: const EdgeInsets.all(14),
			decoration: BoxDecoration(
				color: c.card,
				borderRadius: BorderRadius.circular(16),
				border: Border.all(color: c.border),
			),
			child: Row(
				children: [
					Container(
						padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
						decoration: BoxDecoration(
							color: c.primaryContainer,
							borderRadius: BorderRadius.circular(12),
						),
						child: Text(
							dateLabel,
							textAlign: TextAlign.center,
							style: AppThemes.labelMd.copyWith(color: Colors.white),
						),
					),
					const SizedBox(width: 12),
					Expanded(
						child: Column(
							crossAxisAlignment: CrossAxisAlignment.start,
							children: [
								Text(
									name,
									style: AppThemes.bodyMd.copyWith(
										fontWeight: FontWeight.bold,
										color: c.onSurface,
									),
								),
								const SizedBox(height: 4),
								Text(
									'Vrat and Puja Vidhi',
									style: AppThemes.bodySm.copyWith(color: c.onSurfaceVariant),
								),
							],
						),
					),
					Container(
						padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
						decoration: BoxDecoration(
							color: c.primaryContainer,
							borderRadius: BorderRadius.circular(12),
						),
						child: Text(
							cta,
							style: AppThemes.labelMd.copyWith(color: Colors.white),
						),
					),
				],
			),
		);
	}
}

class _SpiritualTipCard extends StatelessWidget {
	final AsyncValue<String> spiritualTip;

	const _SpiritualTipCard({required this.spiritualTip});

	@override
	Widget build(BuildContext context) {
		return Container(
			decoration: BoxDecoration(
				borderRadius: BorderRadius.circular(16),
				boxShadow: [
					BoxShadow(
						color: AppColors.primaryContainer.withOpacity(0.15),
						blurRadius: 16,
						offset: const Offset(0, 6),
					),
				],
			),
			child: ClipRRect(
				borderRadius: BorderRadius.circular(16),
				child: Stack(
					children: [
						Positioned.fill(
							child: Image.network(
								'https://lh3.googleusercontent.com/aida-public/AB6AXuCFKZyD0LVQwZg86F_GVNdtk0xsue64DOzIzm9rJeYit6z3wd8F4_6khnlqcLl86D9rKDlNSpqs5n-wnW9dKfKC7yCQdoB5c4F23k3uHxrvnCAcn5Tkzxd17865_MDmeTbPvD8-UjWUoZEDxiu-YReq9thHypKbongmHvrdYB9e7rkKQBhf6_VVz3b5Eb6bx8aF4Aq4E3GALvIoDBXIL0WEYUulmNWqtXWFZfIQz6MF9rOQBPAU1gCmWJVOXZphhwISFXWVJ8EYoVs',
								fit: BoxFit.cover,
							),
						),
						Positioned.fill(
							child: Container(
								color: AppColors.primaryContainer.withOpacity(0.75),
							),
						),
						Padding(
							padding: const EdgeInsets.all(16.0),
							child: spiritualTip.when(
								data: (tip) => Column(
									crossAxisAlignment: CrossAxisAlignment.start,
									mainAxisSize: MainAxisSize.min,
									children: [
										const Row(
											children: [
												Icon(
													LucideIcons.sparkles,
													color: Colors.white,
													size: 20,
												),
												SizedBox(width: 8),
												Text(
													'Spiritual Tip',
													style: TextStyle(
														color: Colors.white,
														fontSize: 16,
														fontWeight: FontWeight.bold,
														fontFamily: 'Epilogue',
													),
												),
											],
										),
										const SizedBox(height: 6),
										Text(
											tip,
											style: const TextStyle(
												color: Colors.white,
												fontSize: 13,
												height: 1.3,
												fontFamily: 'Manrope',
											),
										),
									],
								),
								loading: () => const SizedBox(
									height: 80,
									child: Center(
										child: CircularProgressIndicator(color: Colors.white),
									),
								),
								error: (_, __) => const Column(
									crossAxisAlignment: CrossAxisAlignment.start,
									mainAxisSize: MainAxisSize.min,
									children: [
										Row(
											children: [
												Icon(
													LucideIcons.sparkles,
													color: Colors.white,
													size: 20,
												),
												SizedBox(width: 8),
												Text(
													'Spiritual Tip',
													style: TextStyle(
														color: Colors.white,
														fontSize: 16,
														fontWeight: FontWeight.bold,
														fontFamily: 'Epilogue',
													),
												),
											],
										),
										SizedBox(height: 6),
										Text(
											'Practice gratitude and keep your routine steady this month.',
											style: TextStyle(
												color: Colors.white,
												fontSize: 13,
												height: 1.3,
												fontFamily: 'Manrope',
											),
										),
									],
								),
							),
						),
					],
				),
			),
		);
	}
}

class _ErrorState extends StatelessWidget {
	final String message;
	final VoidCallback onRetry;

	const _ErrorState({required this.message, required this.onRetry});

	@override
	Widget build(BuildContext context) {
		final c = AppColorsOf(context);
		return Center(
			child: Padding(
				padding: const EdgeInsets.all(24),
				child: Column(
					mainAxisSize: MainAxisSize.min,
					children: [
						Icon(LucideIcons.alertTriangle, color: c.error, size: 32),
						const SizedBox(height: 12),
						Text(
							'Unable to load Panchang data',
							style: AppThemes.headlineSm.copyWith(fontSize: 16, color: c.onSurface),
						),
						const SizedBox(height: 6),
						Text(
							message,
							textAlign: TextAlign.center,
							style: AppThemes.bodySm.copyWith(color: c.onSurfaceVariant),
						),
						const SizedBox(height: 12),
						ElevatedButton(
							onPressed: onRetry,
							style: ElevatedButton.styleFrom(
								backgroundColor: c.primaryContainer,
								foregroundColor: Colors.white,
							),
							child: Text(
								'Retry',
								style: AppThemes.labelMd.copyWith(color: Colors.white),
							),
						),
					],
				),
			),
		);
	}
}
