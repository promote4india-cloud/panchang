import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../../../constants/app_colors.dart';
import '../../../constants/app_themes.dart';
import '../models/panchang_models.dart';
import '../providers/panchang_providers.dart';

class PanchangDashboardView extends ConsumerWidget {
	const PanchangDashboardView({super.key});

	@override
	Widget build(BuildContext context, WidgetRef ref) {
		final dashboard = ref.watch(panchangDashboardProvider);

		return dashboard.when(
			data: (vm) => SingleChildScrollView(
				padding: const EdgeInsets.only(left: 16, right: 16, top: 20, bottom: 140),
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
											color: AppColors.onSurface,
										),
									),
									const SizedBox(height: 6),
									Text(
										vm.lunarLabel,
										style: AppThemes.bodyMd.copyWith(
											fontWeight: FontWeight.bold,
											color: AppColors.primary,
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
							style: AppThemes.headlineSm,
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
						_SectionHeader(title: 'Daily Rashifal', actionText: 'View All'),
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
						_AstroInsightCard(
							title: 'Astrological Insights',
							subtitle: 'Connect with the cosmos today.',
						),
					],
				),
			),
			loading: () => const Center(
				child: CircularProgressIndicator(color: AppColors.primary),
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
		return Container(
			padding: const EdgeInsets.all(14),
			decoration: BoxDecoration(
				color: AppColors.primaryContainer.withOpacity(0.08),
				borderRadius: BorderRadius.circular(16),
				border: Border.all(color: AppColors.primaryContainer.withOpacity(0.2)),
			),
			child: Row(
				children: [
					Container(
						width: 44,
						height: 44,
						decoration: BoxDecoration(
							color: AppColors.primaryContainer,
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
									style: AppThemes.bodySm,
								),
								const SizedBox(height: 4),
								Text(
									title,
									style: AppThemes.bodyMd.copyWith(
										fontWeight: FontWeight.bold,
										color: AppColors.onSurface,
									),
								),
							],
						),
					),
					const Icon(LucideIcons.chevronRight, color: AppColors.primaryContainer),
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
		return Container(
			padding: const EdgeInsets.all(12),
			decoration: BoxDecoration(
				color: Colors.white,
				borderRadius: BorderRadius.circular(12),
				border: Border.all(color: AppColors.outlineVariant.withOpacity(0.3)),
			),
			child: Column(
				crossAxisAlignment: CrossAxisAlignment.start,
				children: [
					Row(
						children: [
							Icon(icon, size: 16, color: AppColors.primaryContainer),
							const SizedBox(width: 6),
							Text(
								title,
								style: AppThemes.labelMd,
							),
						],
					),
					const SizedBox(height: 8),
					Text(
						value,
						style: AppThemes.bodyMd.copyWith(
							fontWeight: FontWeight.bold,
							color: const Color.fromARGB(255, 70, 72, 72),
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

	const _SectionHeader({
		required this.title,
		this.pillText,
		this.actionText,
	});

	@override
	Widget build(BuildContext context) {
		return Row(
			children: [
				Expanded(
					child: Text(
						title,
						style: AppThemes.headlineSm,
					),
				),
				if (pillText != null)
					Container(
						padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
						decoration: BoxDecoration(
							color: AppColors.primaryContainer,
							borderRadius: BorderRadius.circular(999),
						),
						child: Text(
							pillText!,
							style: AppThemes.labelMd.copyWith(color: Colors.white),
						),
					),
				if (actionText != null)
					Text(
						actionText!,
						style: AppThemes.labelMd.copyWith(
							color: AppColors.primaryContainer,
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
		final toneColor = isPositive ? AppColors.primaryContainer : AppColors.error;
		final bgColor = isPositive
				? Colors.green[50] ?? AppColors.primaryContainer.withOpacity(0.08)
				: AppColors.errorContainerBg;
		const nameColor = AppColors.onSurfaceVariant;

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
					child: ListView.separated(
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
									// border: Border.all(color: toneColor.withOpacity(0.3)),
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
												color: nameColor,
											),
										),
										Text(
											item.timeRange,
											style: AppThemes.bodySm.copyWith(
                        fontWeight: FontWeight.w400,
												color: const Color.fromARGB(255, 1, 1, 1),
											),
										),
									],
								),
							);
						},
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

	IconData _zodiacIcon(String value) {
		switch (value.toLowerCase()) {
			case 'aries':
				return LucideIcons.sun;
			case 'taurus':
				return LucideIcons.trees;
			case 'gemini':
				return LucideIcons.users;
			case 'cancer':
				return LucideIcons.waves;
			case 'leo':
				return LucideIcons.star;
			case 'virgo':
				return LucideIcons.sparkles;
			case 'libra':
				return LucideIcons.moon;
			case 'scorpio':
				return LucideIcons.star;
			case 'sagittarius':
				return LucideIcons.sun;
			case 'capricorn':
				return LucideIcons.trees;
			case 'aquarius':
				return LucideIcons.waves;
			case 'pisces':
				return LucideIcons.moon;
			default:
				return LucideIcons.star;
		}
	}

	String _truncateWords(String value, int limit) {
		final trimmed = value.trim();
		if (trimmed.isEmpty) return trimmed;
		final words = trimmed.split(RegExp(r'\s+'));
		if (words.length <= limit) return trimmed;
		return '${words.take(limit).join(' ')}...';
	}

	@override
	Widget build(BuildContext context) {
		final displayText = _expanded
				? widget.text
				: _truncateWords(widget.text, 20);
		final icon = _zodiacIcon(widget.sign);
		final showSymbol = widget.symbol.trim().isNotEmpty;

		return Container(
			decoration: BoxDecoration(
				color: Colors.white,
				borderRadius: BorderRadius.circular(16),
				border: Border.all(color: AppColors.outlineVariant.withOpacity(0.3)),
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
									border: Border.all(color: AppColors.primaryContainer.withOpacity(0.4)),
									color: AppColors.primaryContainer.withOpacity(0.08),
								),
								child: Center(
									child: showSymbol
										? Text(
											widget.symbol,
											style: AppThemes.bodyMd.copyWith(
												fontWeight: FontWeight.bold,
												color: AppColors.primaryContainer,
											),
										)
										: Icon(icon, color: AppColors.primaryContainer),
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
												color: AppColors.onSurface,
											),
										),
										const SizedBox(height: 6),
										Text(
											displayText,
											style: AppThemes.bodySm,
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
		return Container(
			padding: const EdgeInsets.all(14),
			decoration: BoxDecoration(
				color: Colors.white,
				borderRadius: BorderRadius.circular(16),
				border: Border.all(color: AppColors.outlineVariant.withOpacity(0.3)),
			),
			child: Row(
				children: [
					Container(
						padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
						decoration: BoxDecoration(
							color: AppColors.primaryContainer,
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
										color: AppColors.onSurface,
									),
								),
								const SizedBox(height: 4),
								Text(
									'Vrat and Puja Vidhi',
									style: AppThemes.bodySm,
								),
							],
						),
					),
					Container(
						padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
						decoration: BoxDecoration(
							color: AppColors.primaryContainer,
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

class _AstroInsightCard extends StatelessWidget {
	final String title;
	final String subtitle;

	const _AstroInsightCard({
		required this.title,
		required this.subtitle,
	});

	@override
	Widget build(BuildContext context) {
		return ClipRRect(
			borderRadius: BorderRadius.circular(16),
			child: Stack(
				children: [
					SizedBox(
						height: 160,
						width: double.infinity,
						child: Image.network(
							'https://lh3.googleusercontent.com/aida-public/AB6AXuDjJ4jq73RyQxCpoOLyPSIWgvYSa2sBslby8yViZnO8oFFjP1cbAVbVp7hXqR7r7W4wyxQy-0gqDa5ldnBZOXidQOXjazU3fcPPUqv1nVCi6zyKMaBZzuOIq5mGej9DN0gzB55mmW1t3bdpNgSg7oKEpNgPi-aOBw2aRiX9Xiw3aiclL8v0MGvZnxYzO4ASwYtl6sezwH0b4gDued7HHE6jezRnftO4uFJR4adnv9uJd-uiPMigzQWGp1nc9QXflvHYd6glFP9YntY',
							fit: BoxFit.cover,
						),
					),
					Positioned.fill(
						child: Container(
							decoration: BoxDecoration(
								gradient: LinearGradient(
									colors: [Colors.transparent, Colors.black.withOpacity(0.6)],
									begin: Alignment.topCenter,
									end: Alignment.bottomCenter,
								),
							),
						),
					),
					Positioned(
						left: 16,
						right: 16,
						bottom: 16,
						child: Column(
							crossAxisAlignment: CrossAxisAlignment.start,
							children: [
								Text(
									title,
									style: AppThemes.headlineSm.copyWith(color: Colors.white),
								),
								const SizedBox(height: 4),
								Text(
									subtitle,
									style: AppThemes.bodySm.copyWith(color: Colors.white70),
								),
							],
						),
					),
				],
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
		return Center(
			child: Padding(
				padding: const EdgeInsets.all(24),
				child: Column(
					mainAxisSize: MainAxisSize.min,
					children: [
						const Icon(LucideIcons.alertTriangle, color: AppColors.error, size: 32),
						const SizedBox(height: 12),
						Text(
							'Unable to load Panchang data',
							style: AppThemes.headlineSm.copyWith(fontSize: 16),
						),
						const SizedBox(height: 6),
						Text(
							message,
							textAlign: TextAlign.center,
							style: AppThemes.bodySm,
						),
						const SizedBox(height: 12),
						ElevatedButton(
							onPressed: onRetry,
							style: ElevatedButton.styleFrom(
								backgroundColor: AppColors.primaryContainer,
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
