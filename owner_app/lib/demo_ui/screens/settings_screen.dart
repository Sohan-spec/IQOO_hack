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
              const SectionCard(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16, vertical: 18),
                  child: Row(
                    children: [
                      _Dot(),
                      SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Listening for payments',
                              style: RText.statusTitle,
                            ),
                            Padding(
                              padding: EdgeInsets.only(top: 3),
                              child: Text(
                                "Rahul's Pixel, connected",
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
                      trailing: PillSwitch(
                        value: controller.notifAccessOn,
                        onChanged: (_) => controller.toggleNotifAccess(),
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
  const _Dot();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 9,
      height: 9,
      decoration: const BoxDecoration(
        color: RColors.green,
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
