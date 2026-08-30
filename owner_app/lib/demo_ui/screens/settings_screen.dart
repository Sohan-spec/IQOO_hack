import 'package:flutter/material.dart';

import '../icons.dart';
import '../models.dart';
import '../tokens.dart';
import '../widgets/app_top_bar.dart';
import '../widgets/menu_item.dart';
import '../widgets/pill_switch.dart';
import '../widgets/section_card.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key, required this.controller});

  final DemoController controller;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        return SingleChildScrollView(
          padding: RSpace.screen,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(0, 6, 0, 18),
                child: Row(
                  children: [
                    RIconButton(
                      svg: RIcons.back,
                      size: 20,
                      onTap: controller.closeSettings,
                    ),
                    const Expanded(
                      child: Padding(
                        padding: EdgeInsets.symmetric(horizontal: 10),
                        child: Text(
                          'Settings',
                          style: RText.pageTitleSettings,
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                    const SizedBox(width: 40),
                  ],
                ),
              ),
              SectionCard(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
                  child: Row(
                    children: [
                      _Dot(on: controller.relayConnected),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Listening for payments',
                              style: RText.statusTitle,
                            ),
                            Padding(
                              padding: const EdgeInsets.only(top: 3),
                              child: Text(
                                controller.relayConnected
                                    ? 'Relay connected'
                                    : 'Relay disconnected',
                                style: RText.statusSub,
                              ),
                            ),
                            if (controller.relayMerchantId.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(top: 3),
                                child: Text(
                                  controller.relayMerchantId,
                                  style: RText.statusSub,
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const _GroupLabel('Relay'),
              SectionCard(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        controller.relaySecretConfigured
                            ? 'HMAC secret is stored on this phone'
                            : 'Paste the Modal RELAY_SECRET to connect',
                        style: RText.miTitle,
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: controller.relaySecretController,
                        obscureText: true,
                        autocorrect: false,
                        enableSuggestions: false,
                        style: RText.searchInput,
                        decoration: const InputDecoration(
                          hintText: 'RELAY_SECRET',
                          hintStyle: RText.miSub,
                          isDense: true,
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: GestureDetector(
                          onTap: controller.saveRelaySecret,
                          child: const Text('Save secret', style: RText.link),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const _GroupLabel('Checkout confirm'),
              SectionCard(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        controller.checkoutConfirmSecretConfigured
                            ? 'Confirm secret is stored on this phone'
                            : 'Paste CHECKOUT_CONFIRM_SECRET so C5 can sign /confirm',
                        style: RText.miTitle,
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: controller.checkoutConfirmSecretController,
                        obscureText: true,
                        autocorrect: false,
                        enableSuggestions: false,
                        style: RText.searchInput,
                        decoration: const InputDecoration(
                          hintText: 'CHECKOUT_CONFIRM_SECRET',
                          hintStyle: RText.miSub,
                          isDense: true,
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: GestureDetector(
                          onTap: controller.saveCheckoutConfirmSecret,
                          child: const Text('Save secret', style: RText.link),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const _GroupLabel('Payments'),
              SectionCard(
                child: Column(
                  children: [
                    MenuItem(
                      title: 'Confirm payments automatically',
                      showChevron: false,
                      trailing: PillSwitch(
                        value: controller.confirmAutoOn,
                        onChanged: (_) => controller.toggleConfirmAuto(),
                      ),
                    ),
                    MenuItem(
                      title: 'Notification access',
                      showChevron: false,
                      onTap: controller.openNotificationAccessSettings,
                      trailing: PillSwitch(
                        value: controller.notifAccessOn,
                        onChanged: (_) =>
                            controller.openNotificationAccessSettings(),
                      ),
                    ),
                    MenuItem(
                      title: 'Sound on payment',
                      showChevron: false,
                      trailing: PillSwitch(
                        value: controller.soundOn,
                        onChanged: (_) => controller.toggleSound(),
                      ),
                    ),
                  ],
                ),
              ),
              const _GroupLabel('App'),
              const SectionCard(
                child: MenuItem(
                  title: 'Payment history',
                  showChevron: false,
                  trailing: Text('Export', style: RText.miSub),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot({required this.on});

  final bool on;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 9,
      height: 9,
      decoration: BoxDecoration(
        color: on ? RColors.green : RColors.red,
        shape: BoxShape.circle,
      ),
    );
  }
}

class _GroupLabel extends StatelessWidget {
  const _GroupLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(0, 22, 0, 9),
      child: Text(text.toUpperCase(), style: RText.groupLabel),
    );
  }
}
