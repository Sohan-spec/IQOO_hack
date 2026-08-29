import 'package:flutter/material.dart';

class AccessStatus extends StatelessWidget {
  const AccessStatus({
    super.key,
    required this.granted,
    required this.onOpenSettings,
  });

  final bool granted;
  final VoidCallback onOpenSettings;

  @override
  Widget build(BuildContext context) {
    final color = granted ? const Color(0xFF3DDC97) : const Color(0xFFE85D4C);
    return ListTile(
      onTap: granted ? null : onOpenSettings,
      leading: Icon(granted ? Icons.notifications_active : Icons.notifications_off, color: color),
      title: Text(granted ? 'Notification access granted' : 'Notification access required'),
      subtitle: Text(
        granted
            ? 'PhonePe credits will be forwarded to the matcher.'
            : 'Tap to open system settings. Grant this before the demo.',
      ),
      trailing: granted ? null : const Icon(Icons.open_in_new),
    );
  }
}
