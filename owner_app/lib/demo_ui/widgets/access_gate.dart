import 'package:flutter/material.dart';

import '../tokens.dart';

/// Full-shell R2 gate. Shown until the NotificationListenerService is enabled.
/// POST_NOTIFICATIONS ("Allow notifications") is a different permission and
/// does not dismiss this screen.
class DemoAccessGate extends StatelessWidget {
  const DemoAccessGate({super.key, required this.onOpenSettings});

  final VoidCallback onOpenSettings;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: RColors.bg,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.notifications_off, size: 48, color: RColors.red),
            const SizedBox(height: 20),
            const Text('Notification access required', style: RText.secH2),
            const SizedBox(height: 12),
            const Text(
              'Android\'s Allow notifications popup is not enough. Open system settings and turn on Relay Owner under Notification access (sometimes labelled Device & app notifications).',
              style: RText.empty,
            ),
            const SizedBox(height: 28),
            FilledButton(
              onPressed: onOpenSettings,
              style: FilledButton.styleFrom(
                backgroundColor: RColors.purple,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(RRadii.button),
                ),
              ),
              child: const Text('Open notification access'),
            ),
          ],
        ),
      ),
    );
  }
}
