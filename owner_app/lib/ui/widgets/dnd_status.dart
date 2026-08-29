import 'package:flutter/material.dart';
import 'package:owner_app/notification/notification_bridge.dart';

class DndStatus extends StatelessWidget {
  const DndStatus({super.key, required this.filter});

  final int filter;

  @override
  Widget build(BuildContext context) {
    final on = InterruptionFilter.isDndOn(filter);
    final color = on ? const Color(0xFFE8A838) : const Color(0xFF3DDC97);
    return ListTile(
      leading: Icon(on ? Icons.do_not_disturb_on : Icons.do_not_disturb_off, color: color),
      title: Text('DND: ${InterruptionFilter.label(filter)}'),
      subtitle: Text(
        on
            ? 'R5: interruption filter is not ALL. PhonePe credits may be delayed or suppressed.'
            : 'Interruption filter is ALL. Notification delivery is not silenced.',
      ),
    );
  }
}
