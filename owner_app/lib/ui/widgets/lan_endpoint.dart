import 'dart:io';

import 'package:flutter/material.dart';

class LanEndpoint extends StatelessWidget {
  const LanEndpoint({super.key, required this.urls});

  final List<String> urls;

  static Future<List<String>> discover() async {
    final urls = <String>[];
    for (final iface in await NetworkInterface.list()) {
      for (final addr in iface.addresses) {
        if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
          urls.add('http://${addr.address}:8787');
        }
      }
    }
    return urls;
  }

  @override
  Widget build(BuildContext context) {
    final text = urls.isEmpty
        ? 'No LAN address yet. Connect hotspot, then reopen.'
        : urls.map((url) => '$url  (POST /v1/transactions)').join('\n');
    return ListTile(
      leading: const Icon(Icons.wifi_tethering),
      title: const Text('Storefront endpoint'),
      subtitle: Text(text),
    );
  }
}
