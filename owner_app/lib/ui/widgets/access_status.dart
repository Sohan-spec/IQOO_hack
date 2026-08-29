import 'package:flutter/material.dart';

/// Full-body R2 gate. Shown instead of the operator UI until notification access is granted.
class AccessGate extends StatelessWidget {
  const AccessGate({super.key, required this.onOpenSettings});

  final VoidCallback onOpenSettings;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Material(
      color: theme.scaffoldBackgroundColor,
      child: InkWell(
        onTap: onOpenSettings,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.notifications_off, size: 48, color: Color(0xFFE85D4C)),
              const SizedBox(height: 20),
              Text('Notification access required', style: theme.textTheme.titleLarge),
              const SizedBox(height: 12),
              Text(
                'Grant notification access before anything else is usable. Tap to open system settings.',
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class AccessStatus extends StatelessWidget {
  const AccessStatus({super.key});

  @override
  Widget build(BuildContext context) {
    return const ListTile(
      leading: Icon(Icons.notifications_active, color: Color(0xFF3DDC97)),
      title: Text('Notification access granted'),
      subtitle: Text('PhonePe credits will be forwarded to the matcher.'),
    );
  }
}
