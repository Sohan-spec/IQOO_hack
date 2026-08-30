import 'package:flutter/material.dart';

class PendingList extends StatelessWidget {
  const PendingList({
    super.key,
    required this.pending,
    required this.onConfirm,
  });

  final List<Map<String, dynamic>> pending;
  final void Function(String sessionId) onConfirm;

  @override
  Widget build(BuildContext context) {
    if (pending.isEmpty) {
      return const ListTile(
        title: Text('No pending transactions'),
        subtitle: Text('Waiting for the storefront to enqueue.'),
      );
    }
    return Column(
      children: [
        for (final row in pending)
          ListTile(
            title: Text('${row['customer_name']}  ₹${row['amount']}'),
            subtitle: Text(
              [
                if ((row['customer_phone'] ?? '').toString().isNotEmpty)
                  row['customer_phone'],
                if ((row['customer_email'] ?? '').toString().isNotEmpty)
                  row['customer_email'],
                '${row['session_id']}  ·  ${row['elapsed_seconds']}s',
              ].join('\n'),
            ),
            trailing: TextButton(
              onPressed: () => onConfirm(row['session_id'] as String),
              child: const Text('Confirm'),
            ),
          ),
      ],
    );
  }
}
