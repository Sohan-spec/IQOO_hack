import 'package:flutter/material.dart';

import '../icons.dart';
import '../models.dart';
import '../tokens.dart';
import '../widgets/app_top_bar.dart';
import '../widgets/menu_item.dart';
import '../widgets/section_card.dart';

class AccountScreen extends StatelessWidget {
  const AccountScreen({super.key, required this.controller});

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
              AppTopBar(onSettings: controller.openSettings),
              SectionCard(
                padding: const EdgeInsets.fromLTRB(16, 18, 16, 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        _ProfileAvatar(),
                        SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Rahul Sharma', style: RText.profileName),
                              Padding(
                                padding: EdgeInsets.only(top: 4),
                                child: Text(
                                  'rahul@shopstore.in',
                                  style: RText.profileEmail,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const Padding(
                      padding: EdgeInsets.only(top: 16),
                      child: Text('View profile ›', style: RText.profileLink),
                    ),
                  ],
                ),
              ),
              const _GroupLabel('Business'),
              const SectionCard(
                child: Column(
                  children: [
                    MenuItem(
                      iconSvg: RIcons.miBank,
                      title: 'UPI ID',
                      subtitle: 'shopstore@ibl',
                    ),
                    MenuItem(
                      iconSvg: RIcons.miHome,
                      title: 'Business name',
                      subtitle: 'ShopStore',
                    ),
                    MenuItem(
                      iconSvg: RIcons.miDoc,
                      title: 'Business details',
                      subtitle: 'View and edit your business information',
                    ),
                    MenuItem(
                      iconSvg: RIcons.miPhone,
                      title: 'Device name',
                      subtitle: "Rahul's Pixel",
                    ),
                  ],
                ),
              ),
              const _GroupLabel('Preferences'),
              SectionCard(
                child: Column(
                  children: [
                    const MenuItem(
                      iconSvg: RIcons.miBell,
                      title: 'Notifications',
                      subtitle: 'Manage notification settings',
                    ),
                    MenuItem(
                      iconSvg: RIcons.miShield,
                      title: 'Notification access',
                      subtitle: controller.notifAccessOn ? 'Enabled' : 'Off',
                      subtitleOk: controller.notifAccessOn,
                      onTap: controller.openSettings,
                    ),
                    const MenuItem(
                      iconSvg: RIcons.miHelp,
                      title: 'Help & support',
                      subtitle: 'Get help and contact support',
                    ),
                    const MenuItem(
                      iconSvg: RIcons.miInfo,
                      title: 'About Relay',
                      subtitle: 'Version 1.0.0',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SectionCard(
                child: MenuItem(
                  iconSvg: RIcons.miLogout,
                  title: 'Log out',
                  danger: true,
                  showChevron: false,
                  onTap: () => controller.showToast('Logged out'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ProfileAvatar extends StatelessWidget {
  const _ProfileAvatar();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 52,
      height: 52,
      alignment: Alignment.center,
      decoration: const BoxDecoration(
        color: RColors.purpleTint,
        shape: BoxShape.circle,
      ),
      child: const Text('RS', style: RText.profileAvatar),
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
