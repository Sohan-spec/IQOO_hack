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
import 'package:owner_app/ui/widgets/relay_status.dart';

class OperatorScreen extends StatefulWidget {
  const OperatorScreen({super.key});

  @override
  State<OperatorScreen> createState() => _OperatorScreenState();
}

class _OperatorScreenState extends State<OperatorScreen> {
  final _python = PythonClient();
  final _device = DeviceBridge();
  final _callbackController = TextEditingController();
  final _secretController = TextEditingController();
  final _confirmSecretController = TextEditingController();
  Timer? _poll;
  Snapshot? _snapshot;
  bool _access = false;
  bool _batteryOk = false;
  bool _callbackPushed = false;
  int _filter = 0;
  List<String> _lan = [];
  bool _relayConnected = false;
  String _relayMerchantId = '';
  bool _relaySecretConfigured = false;
  bool _checkoutConfirmSecretConfigured = false;
  String? _error;
  String? _callbackError;

  @override
  void initState() {
    super.initState();
    _device.runSetupPrompts();
    _pushDefaultCallbackUrl();
    _refresh();
    _poll = Timer.periodic(const Duration(milliseconds: 500), (_) => _refresh());
  }

  @override
  void dispose() {
    _poll?.cancel();
    _callbackController.dispose();
    _secretController.dispose();
    _confirmSecretController.dispose();
    super.dispose();
  }

  Future<void> _pushDefaultCallbackUrl() async {
    if (_callbackPushed) {
      return;
    }
    try {
      final url = await _device.getDefaultCallbackUrl();
      if (mounted) {
        _callbackController.text = url;
      }
      await _python.setDefaultCallbackUrl(url);
      _callbackPushed = true;
    } catch (_) {
      // Python may still be binding 8787; _refresh retries until it succeeds.
    }
  }

  /// Re-push the device-persisted default if Python lost it (process restart).
  Future<void> _resyncDefaultCallbackUrl(Snapshot snapshot) async {
    try {
      final deviceUrl = await _device.getDefaultCallbackUrl();
      if (snapshot.defaultCallbackUrl.trim() == deviceUrl.trim()) {
        return;
      }
      await _python.setDefaultCallbackUrl(deviceUrl);
    } catch (_) {
      // Next poll retries. Keep _callbackPushed; mismatch detection recovers
      // a restarted Python process without clobbering an in-progress edit.
    }
  }

  Future<void> _refresh() async {
    var access = _access;
    try {
      access = await _device.notificationAccessGranted();
    } catch (_) {
      // Keep the last known value; fail closed on the initial false.
    }
    if (mounted) {
      setState(() => _access = access);
    }
    try {
      final filter = await _device.interruptionFilter();
      final batteryOk = await _device.batteryOptimizationIgnored();
      final lan = await LanEndpoint.discover();
      final relayConnected = await _device.relayConnected();
      final relayMerchantId = await _device.relayMerchantId();
      final relaySecretConfigured = await _device.relaySecretConfigured();
      final checkoutConfirmSecretConfigured =
          await _device.checkoutConfirmSecretConfigured();
      if (mounted) {
        setState(() {
          _filter = filter;
          _batteryOk = batteryOk;
          _lan = lan;
          _relayConnected = relayConnected;
          _relayMerchantId = relayMerchantId;
          _relaySecretConfigured = relaySecretConfigured;
          _checkoutConfirmSecretConfigured = checkoutConfirmSecretConfigured;
        });
      }
    } catch (_) {
      // Leave DND / battery / LAN / relay rows on the last successful poll.
    }
    await _pushDefaultCallbackUrl();
    try {
      final snapshot = await _python.snapshot();
      if (!mounted) {
        return;
      }
      await _resyncDefaultCallbackUrl(snapshot);
      if (!mounted) {
        return;
      }
      setState(() {
        _snapshot = snapshot;
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
    try {
      await _python.manualConfirm(sessionId);
    } catch (error) {
      if (mounted) {
        setState(() => _error = error.toString());
      }
      return;
    }
    await _refresh();
  }

  Future<void> _saveRelaySecret() async {
    final secret = _secretController.text.trim();
    if (secret.isEmpty) {
      return;
    }
    await _device.setRelaySecret(secret);
    _secretController.clear();
  }

  Future<void> _saveCheckoutConfirmSecret() async {
    final secret = _confirmSecretController.text.trim();
    if (secret.isEmpty) {
      return;
    }
    await _device.setCheckoutConfirmSecret(secret);
    _confirmSecretController.clear();
  }

  Future<void> _saveDefaultCallbackUrl() async {
    final url = _callbackController.text.trim();
    if (url.isNotEmpty && !url.startsWith('http://') && !url.startsWith('https://')) {
      setState(() => _callbackError = 'Must start with http:// or https://');
      return;
    }
    _callbackController.text = url;
    setState(() => _callbackError = null);
    try {
      await _device.setDefaultCallbackUrl(url);
      await _python.setDefaultCallbackUrl(url);
      _callbackPushed = true;
    } catch (error) {
      _callbackPushed = false;
      if (mounted) {
        setState(() => _callbackError = error.toString());
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Relay owner')),
      body: _access ? _operatorBody() : AccessGate(onOpenSettings: _device.openNotificationAccessSettings),
    );
  }

  Widget _operatorBody() {
    final snapshot = _snapshot;
    return ListView(
      children: [
        if (_error != null)
          ListTile(
            title: const Text('Python backend unreachable'),
            subtitle: Text(_error!),
          ),
        const AccessStatus(),
        RelayStatus(connected: _relayConnected, merchantId: _relayMerchantId),
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
        ExpansionTile(
          title: const Text('Relay HMAC secret'),
          subtitle: Text(
            _relaySecretConfigured
                ? 'Stored on device. Paste again to rotate.'
                : 'Paste the Modal RELAY_SECRET so this phone can connect',
          ),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: TextField(
                controller: _secretController,
                obscureText: true,
                autocorrect: false,
                enableSuggestions: false,
                decoration: const InputDecoration(
                  labelText: 'RELAY_SECRET',
                ),
              ),
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: _saveRelaySecret,
                child: const Text('Save'),
              ),
            ),
          ],
        ),
        ExpansionTile(
          title: const Text('Checkout confirm secret'),
          subtitle: Text(
            _checkoutConfirmSecretConfigured
                ? 'Stored on device. Paste again to rotate.'
                : 'Paste CHECKOUT_CONFIRM_SECRET so C5 can sign /confirm',
          ),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: TextField(
                controller: _confirmSecretController,
                obscureText: true,
                autocorrect: false,
                enableSuggestions: false,
                decoration: const InputDecoration(
                  labelText: 'CHECKOUT_CONFIRM_SECRET',
                ),
              ),
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: _saveCheckoutConfirmSecret,
                child: const Text('Save'),
              ),
            ),
          ],
        ),
        ExpansionTile(
          title: const Text('Default callback URL'),
          subtitle: const Text('Used when the storefront omits callback_url'),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: TextField(
                controller: _callbackController,
                keyboardType: TextInputType.url,
                autocorrect: false,
                decoration: InputDecoration(
                  labelText: 'http:// or https:// URL',
                  errorText: _callbackError,
                ),
              ),
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: _saveDefaultCallbackUrl,
                child: const Text('Save'),
              ),
            ),
          ],
        ),
        MatchBanner(match: snapshot?.recentMatches.firstOrNull),
        const Divider(),
        const ListTile(title: Text('Pending')),
        PendingList(pending: snapshot?.pending ?? [], onConfirm: _confirm),
        const Divider(),
        const ListTile(title: Text('Credit events')),
        CreditFeed(credits: snapshot?.recentCredits ?? []),
      ],
    );
  }
}
