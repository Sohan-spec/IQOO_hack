import 'package:flutter/material.dart';

import 'icons.dart';
import 'models.dart';
import 'screens/account_screen.dart';
import 'screens/home_screen.dart';
import 'screens/payments_screen.dart';
import 'screens/settings_screen.dart';
import 'tokens.dart';
import 'widgets/access_gate.dart';
import 'widgets/confirm_sheet.dart';
import 'widgets/toast.dart';

class DemoShell extends StatefulWidget {
  const DemoShell({super.key});

  @override
  State<DemoShell> createState() => _DemoShellState();
}

class _DemoShellState extends State<DemoShell> {
  late final DemoController controller;

  @override
  void initState() {
    super.initState();
    controller = DemoController();
    controller.start();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        return PopScope(
          canPop: !controller.sheetOpen && !controller.showingSettings,
          onPopInvokedWithResult: (didPop, _) {
            if (didPop) return;
            if (controller.sheetOpen) {
              controller.closeSheet();
            } else if (controller.showingSettings) {
              controller.closeSettings();
            }
          },
          child: Stack(
            children: [
              Scaffold(
                backgroundColor: RColors.bg,
                body: SafeArea(
                  bottom: false,
                  child: IndexedStack(
                    index: controller.showingSettings
                        ? 3
                        : controller.currentTab,
                    children: [
                      HomeScreen(controller: controller),
                      PaymentsScreen(controller: controller),
                      AccountScreen(controller: controller),
                      SettingsScreen(controller: controller),
                    ],
                  ),
                ),
                bottomNavigationBar: _TabBar(
                  activeIndex: controller.lastTab,
                  onTap: controller.goToTab,
                ),
              ),
              Positioned.fill(
                child: IgnorePointer(
                  ignoring: !controller.sheetOpen,
                  child: AnimatedOpacity(
                    opacity: controller.sheetOpen ? 1 : 0,
                    duration: const Duration(milliseconds: 260),
                    curve: Curves.ease,
                    child: GestureDetector(
                      onTap: controller.closeSheet,
                      behavior: HitTestBehavior.opaque,
                      child: const ColoredBox(color: RColors.scrim),
                    ),
                  ),
                ),
              ),
              if (controller.sheetPayment != null)
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  child: IgnorePointer(
                    ignoring: !controller.sheetOpen,
                    child: AnimatedSlide(
                      offset: controller.sheetOpen
                          ? Offset.zero
                          : const Offset(0, 1.02),
                      duration: const Duration(milliseconds: 340),
                      curve: const Cubic(0.2, 0.9, 0.25, 1.0),
                      child: ConfirmSheet(
                        payment: controller.sheetPayment!,
                        onConfirm: () {
                          controller.confirmPayment();
                        },
                        onReject: controller.rejectPayment,
                      ),
                    ),
                  ),
                ),
              Positioned(
                left: 20,
                right: 20,
                bottom: 88,
                child: IgnorePointer(
                  child: AnimatedOpacity(
                    opacity: controller.toastVisible ? 1 : 0,
                    duration: const Duration(milliseconds: 240),
                    curve: Curves.ease,
                    child: AnimatedSlide(
                      offset: controller.toastVisible
                          ? Offset.zero
                          : const Offset(0, 0.22),
                      duration: const Duration(milliseconds: 240),
                      curve: Curves.ease,
                      child: RToast(message: controller.toastMessage),
                    ),
                  ),
                ),
              ),
              if (!controller.notifAccessOn)
                Positioned.fill(
                  child: DemoAccessGate(
                    onOpenSettings: controller.openNotificationAccessSettings,
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}

class _TabBar extends StatelessWidget {
  const _TabBar({required this.activeIndex, required this.onTap});

  final int activeIndex;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: RColors.cardBg,
        border: Border(
          top: BorderSide(color: RColors.tabBorder, width: 1),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 11, 8, 14),
          child: Row(
            children: [
              _Tab(
                icon: RIcons.tabHome,
                label: 'Home',
                active: activeIndex == 0,
                onTap: () => onTap(0),
              ),
              _Tab(
                icon: RIcons.tabPayments,
                label: 'Payments',
                active: activeIndex == 1,
                onTap: () => onTap(1),
              ),
              _Tab(
                icon: RIcons.tabAccount,
                label: 'Account',
                active: activeIndex == 2,
                onTap: () => onTap(2),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Tab extends StatelessWidget {
  const _Tab({
    required this.icon,
    required this.label,
    required this.active,
    required this.onTap,
  });

  final String icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = active ? RColors.purple : RColors.tabIdle;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              RSvg(icon, width: 26, height: 26, color: color),
              const SizedBox(height: 7),
              Text(label, style: active ? RText.tabOn : RText.tab),
            ],
          ),
        ),
      ),
    );
  }
}
