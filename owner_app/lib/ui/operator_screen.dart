import 'dart:async';

import 'package:flutter/material.dart';
import 'package:owner_app/api/python_client.dart';
import 'package:owner_app/notification/notification_bridge.dart';
import 'package:owner_app/ui/widgets/access_status.dart';
import 'package:owner_app/ui/widgets/credit_feed.dart';
import 'package:owner_app/ui/widgets/dnd_status.dart';
import 'package:owner_app/ui/widgets/lan_endpoint.dart';
import 'package:owner_app/ui/widgets/match_banner.dart';
import 'package:owner_app/ui/widgets/pending_list.dart';

class OperatorScreen extends StatefulWidget {
  const OperatorScreen({super.key});

  @override
  State<OperatorScreen> createState() => _OperatorScreenState();
}

class _OperatorScreenState extends State<OperatorScreen> {
  final _python = PythonClient();
  final _device = DeviceBridge();
  Timer? _poll;
  Snapshot? _snapshot;
  bool _access = false;
  bool _batteryOk = false;
  int _filter = 0;
  List<String> _lan = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _device.requestPostNotifications();
    _refresh();
    _poll = Timer.periodic(const Duration(milliseconds: 500), (_) => _refresh());
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final snapshot = await _python.snapshot();
      final access = await _device.notificationAccessGranted();
      final filter = await _device.interruptionFilter();
      final batteryOk = await _device.batteryOptimizationIgnored();
      final lan = await LanEndpoint.discover();
      if (!mounted) {
        return;
      }
      setState(() {
        _snapshot = snapshot;
        _access = access;
        _filter = filter;
        _batteryOk = batteryOk;
        _lan = lan;
        _error = null;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _error = error.toString());
    }
  }

  Future<void> _confirm(String sessionId) async {
    await _python.manualConfirm(sessionId);
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    final snapshot = _snapshot;
    return Scaffold(
      appBar: AppBar(title: const Text('Relay owner')),
      body: ListView(
        children: [
          if (_error != null)
            ListTile(
              title: const Text('Python backend unreachable'),
              subtitle: Text(_error!),
            ),
          AccessStatus(
            granted: _access,
            onOpenSettings: _device.openNotificationAccessSettings,
          ),
          DndStatus(filter: _filter),
          ListTile(
            leading: Icon(
              _batteryOk ? Icons.battery_charging_full : Icons.battery_alert,
              color: _batteryOk ? const Color(0xFF3DDC97) : const Color(0xFFE8A838),
            ),
            title: Text(_batteryOk ? 'Battery optimization off' : 'Allow background run'),
            subtitle: const Text(
              'Screen can be off. On iQOO also: Autostart on, lock Relay in recents, do not swipe it away.',
            ),
            onTap: _batteryOk ? null : _device.requestIgnoreBatteryOptimizations,
          ),
          LanEndpoint(urls: _lan),
          MatchBanner(match: snapshot?.recentMatches.firstOrNull),
          const Divider(),
          const ListTile(title: Text('Pending')),
          PendingList(pending: snapshot?.pending ?? [], onConfirm: _confirm),
          const Divider(),
          const ListTile(title: Text('Credit events')),
          CreditFeed(credits: snapshot?.recentCredits ?? []),
        ],
      ),
    );
  }
}
