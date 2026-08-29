import 'package:flutter/material.dart';

import '../models.dart';
import '../tokens.dart';
import '../widgets/app_top_bar.dart';
import '../widgets/payment_row.dart';
import '../widgets/section_card.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.controller});

  final DemoController controller;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        final pending = controller.pending;
        final recent = controller.successful.take(3).toList();
        return SingleChildScrollView(
          padding: RSpace.screen,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AppTopBar(onSettings: controller.openSettings),
              _HeroCard(total: controller.total, count: controller.count),
              const SizedBox(height: 20),
              SectionCard(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Column(
                  children: [
                    _SecHead(
                      title: 'Pending payments',
                      badge: pending.length,
                      onViewAll: () =>
                          controller.openPayments(PayStatus.pending),
                    ),
                    if (pending.isEmpty)
                      const Padding(
                        padding: EdgeInsets.fromLTRB(0, 14, 0, 16),
                        child: Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            'Nothing waiting. New payments show up here.',
                            style: RText.empty,
                          ),
                        ),
                      )
                    else
                      for (final p in pending)
                        PaymentRow(
                          payment: p,
                          variant: PaymentRowVariant.home,
                          onTap: () => controller.openSheet(p),
                        ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              SectionCard(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Column(
                  children: [
                    _SecHead(
                      title: 'Recent payments',
                      onViewAll: () =>
                          controller.openPayments(PayStatus.successful),
                    ),
                    for (final p in recent)
                      PaymentRow(
                        payment: p,
                        variant: PaymentRowVariant.home,
                      ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _SecHead extends StatelessWidget {
  const _SecHead({
    required this.title,
    required this.onViewAll,
    this.badge,
  });

  final String title;
  final VoidCallback onViewAll;
  final int? badge;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(0, 18, 0, 4),
      child: Row(
        children: [
          Expanded(
            child: Row(
              children: [
                Flexible(child: Text(title, style: RText.secH2)),
                if (badge != null && badge! > 0) ...[
                  const SizedBox(width: 10),
                  Container(
                    constraints: const BoxConstraints(minWidth: 22),
                    height: 22,
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: RColors.purple,
                      borderRadius: BorderRadius.circular(RRadii.pill),
                    ),
                    child: Text('$badge', style: RText.badge),
                  ),
                ],
              ],
            ),
          ),
          GestureDetector(
            onTap: onViewAll,
            child: const Text('View all', style: RText.link),
          ),
        ],
      ),
    );
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({required this.total, required this.count});

  final int total;
  final int count;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      clip: true,
      child: Stack(
        children: [
          Positioned(
            right: -48,
            top: 0,
            bottom: 0,
            width: 370 / 293 * 210,
            child: IgnorePointer(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final top = constraints.maxHeight * 0.5 - 210 * 0.46;
                  return Stack(
                    clipBehavior: Clip.none,
                    children: [
                      Positioned(
                        top: top,
                        right: 0,
                        child: Opacity(
                          opacity: 0.14,
                          child: ShaderMask(
                            blendMode: BlendMode.dstIn,
                            shaderCallback: (bounds) {
                              return const LinearGradient(
                                begin: Alignment(-0.9063, -0.4226),
                                end: Alignment(0.9063, 0.4226),
                                colors: [
                                  Color(0x00000000),
                                  Color(0xFF000000),
                                  Color(0xFF000000),
                                ],
                                stops: [0.08, 0.46, 1.0],
                              ).createShader(bounds);
                            },
                            child: Image.asset(
                              'assets/images/logo.png',
                              height: 210,
                              fit: BoxFit.fitHeight,
                              filterQuality: FilterQuality.medium,
                            ),
                          ),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 34),
            child: LayoutBuilder(
              builder: (context, constraints) {
                return Align(
                  alignment: Alignment.centerLeft,
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      maxWidth: constraints.maxWidth * 0.68,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Total received today',
                          style: RText.heroLabel,
                        ),
                        Padding(
                          padding: const EdgeInsets.only(top: 11, bottom: 9),
                          child: Text(money(total), style: RText.heroAmount),
                        ),
                        Text('$count payments', style: RText.heroSub),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
