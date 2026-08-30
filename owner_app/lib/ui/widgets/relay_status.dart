import 'package:flutter/material.dart';

class RelayStatus extends StatelessWidget {
  const RelayStatus({
    super.key,
    required this.connected,
    required this.merchantId,
  });

  final bool connected;
  final String merchantId;

  @override
  Widget build(BuildContext context) {
    final color = connected ? const Color(0xFF3DDC97) : const Color(0xFFE85D4C);
    final id = merchantId.isEmpty ? 'not issued yet' : merchantId;
    return ListTile(
      leading: Icon(connected ? Icons.cloud_done : Icons.cloud_off, color: color),
      title: Text(connected ? 'Relay connected' : 'Relay disconnected'),
      subtitle: Text(
        connected
            ? 'Storefront can enqueue from any network.\nmerchant_id $id'
            : 'Waiting for wss:// relay. merchant_id $id',
      ),
      isThreeLine: true,
    );
  }
}
