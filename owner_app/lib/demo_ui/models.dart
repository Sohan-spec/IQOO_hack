import 'dart:async';

import 'package:flutter/material.dart';
import 'package:owner_app/api/python_client.dart';
import 'package:owner_app/notification/notification_bridge.dart';

import 'mapping.dart';
import 'tokens.dart';

enum PayStatus { pending, successful, failed }

extension PayStatusX on PayStatus {
  String get label => switch (this) {
        PayStatus.pending => 'Pending',
        PayStatus.successful => 'Successful',
        PayStatus.failed => 'Failed',
      };

  Color get color => switch (this) {
        PayStatus.pending => RColors.purple,
        PayStatus.successful => RColors.green,
        PayStatus.failed => RColors.red,
      };
}

class Payment {
  Payment({
    required this.id,
    required this.name,
    required this.amount,
    required this.status,
    required this.group,
    required this.clock,
    required this.relative,
    this.ref,
    this.email,
    this.phone,
  });

  final String id;
  String name;
  num amount;
  PayStatus status;
  String group;
  String clock;
  String relative;
  String? ref;
  String? email;
  String? phone;
}

String money(num n) {
  final negative = n < 0;
  final scaled = (n.abs() * 100).round();
  final rupees = scaled ~/ 100;
  final paise = scaled % 100;
  var s = rupees.toString();
  String grouped;
  if (s.length <= 3) {
    grouped = s;
  } else {
    final last3 = s.substring(s.length - 3);
    s = s.substring(0, s.length - 3);
    final parts = <String>[last3];
    while (s.length > 2) {
      parts.insert(0, s.substring(s.length - 2));
      s = s.substring(0, s.length - 2);
    }
    if (s.isNotEmpty) {
      parts.insert(0, s);
    }
    grouped = parts.join(',');
  }
  var out = '₹$grouped';
  if (paise != 0) {
    out = '$out.${paise.toString().padLeft(2, '0')}';
  }
  if (negative) {
    return '-$out';
  }
  return out;
}

String initials(String name) {
  final chars = name
      .split(' ')
      .where((w) => w.isNotEmpty)
      .map((w) => w[0])
      .join()
      .toUpperCase();
  if (chars.length <= 2) {
    return chars;
  }
  return chars.substring(0, 2);
}

class DemoController extends ChangeNotifier with WidgetsBindingObserver {
  DemoController({
    PythonClient? python,
    DeviceBridge? device,
  })  : _python = python ?? PythonClient(),
        _device = device ?? DeviceBridge();

  final PythonClient _python;
  final DeviceBridge _device;
  final searchController = TextEditingController();
  final relaySecretController = TextEditingController();
  final checkoutConfirmSecretController = TextEditingController();

  List<Payment> payments = [];
  num total = 0;
  int count = 0;
  int currentTab = 0;
  int lastTab = 0;
  bool showingSettings = false;
  PayStatus? chipFilter;
  String searchQuery = '';
  bool notifAccessOn = false;
  bool relayConnected = false;
  String relayMerchantId = '';
  bool relaySecretConfigured = false;
  bool checkoutConfirmSecretConfigured = false;
  bool confirmAutoOn = false;
  bool soundOn = true;
  bool unreachable = false;

  Payment? sheetPayment;
  bool sheetOpen = false;

  String toastMessage = 'Payment confirmed';
  bool toastVisible = false;
  Timer? _toastTimer;
  Timer? _poll;
  bool _started = false;
  bool _disposed = false;

  List<Payment> get pending =>
      payments.where((p) => p.status == PayStatus.pending).toList();

  List<Payment> get successful =>
      payments.where((p) => p.status == PayStatus.successful).toList();

  List<Payment> get filteredPayments {
    final q = searchQuery.toLowerCase();
    return payments.where((p) {
      if (chipFilter != null && p.status != chipFilter) {
        return false;
      }
      if (q.isNotEmpty && !p.name.toLowerCase().contains(q)) {
        return false;
      }
      return true;
    }).toList();
  }

  void start() {
    if (_started) {
      return;
    }
    _started = true;
    WidgetsBinding.instance.addObserver(this);
    _device.runSetupPrompts();
    _refresh();
    _poll = Timer.periodic(const Duration(milliseconds: 500), (_) => _refresh());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _device.runSetupPrompts();
      _refresh();
    }
  }

  Future<void> _refresh() async {
    try {
      final access = await _device.notificationAccessGranted();
      final relay = await _device.relayConnected();
      final merchantId = await _device.relayMerchantId();
      final secretOn = await _device.relaySecretConfigured();
      final confirmOn = await _device.checkoutConfirmSecretConfigured();
      if (!_disposed) {
        notifAccessOn = access;
        relayConnected = relay;
        relayMerchantId = merchantId;
        relaySecretConfigured = secretOn;
        checkoutConfirmSecretConfigured = confirmOn;
        notifyListeners();
      }
    } catch (_) {
      // Keep last known access; fail closed on the initial false.
    }
    try {
      final snap = await _python.snapshot();
      if (_disposed) {
        return;
      }
      payments = paymentsFromSnapshot(snap);
      final today = todayTotals(snap);
      total = today.total;
      count = today.count;
      unreachable = false;
    } catch (_) {
      unreachable = true;
    }
    if (!_disposed) {
      notifyListeners();
    }
  }

  void goToTab(int index) {
    currentTab = index;
    lastTab = index;
    showingSettings = false;
    notifyListeners();
  }

  void openSettings() {
    showingSettings = true;
    notifyListeners();
  }

  void closeSettings() {
    showingSettings = false;
    currentTab = lastTab;
    notifyListeners();
  }

  void openPayments(PayStatus filter) {
    chipFilter = filter;
    goToTab(1);
  }

  void setChip(PayStatus? filter) {
    chipFilter = filter;
    notifyListeners();
  }

  void setQuery(String q) {
    searchQuery = q;
    notifyListeners();
  }

  void openSheet(Payment p) {
    sheetPayment = p;
    sheetOpen = true;
    notifyListeners();
  }

  void closeSheet() {
    if (!sheetOpen) {
      return;
    }
    sheetOpen = false;
    notifyListeners();
  }

  Future<void> confirmPayment() async {
    final p = sheetPayment;
    if (p == null) {
      return;
    }
    closeSheet();
    try {
      await _python.manualConfirm(p.id);
      showToast('Payment confirmed');
    } catch (_) {
      showToast('Already confirmed');
    }
    if (!_disposed) {
      await _refresh();
    }
  }

  void rejectPayment() {
    closeSheet();
  }

  void openNotificationAccessSettings() {
    _device.openNotificationAccessSettings();
  }

  Future<void> saveRelaySecret() async {
    final secret = relaySecretController.text.trim();
    if (secret.isEmpty) {
      showToast('Paste the Modal RELAY_SECRET first');
      return;
    }
    try {
      await _device.setRelaySecret(secret);
      relaySecretController.clear();
      showToast('Relay secret saved');
    } catch (_) {
      showToast('Could not save relay secret');
    }
    await _refresh();
  }

  Future<void> saveCheckoutConfirmSecret() async {
    final secret = checkoutConfirmSecretController.text.trim();
    if (secret.isEmpty) {
      showToast('Paste CHECKOUT_CONFIRM_SECRET first');
      return;
    }
    try {
      await _device.setCheckoutConfirmSecret(secret);
      checkoutConfirmSecretController.clear();
      showToast('Checkout confirm secret saved');
    } catch (_) {
      showToast('Could not save checkout confirm secret');
    }
    await _refresh();
  }

  void toggleConfirmAuto() {
    confirmAutoOn = !confirmAutoOn;
    notifyListeners();
  }

  void toggleSound() {
    soundOn = !soundOn;
    notifyListeners();
  }

  void showToast(String msg) {
    if (_disposed) {
      return;
    }
    toastMessage = msg;
    toastVisible = true;
    notifyListeners();
    _toastTimer?.cancel();
    _toastTimer = Timer(const Duration(milliseconds: 2200), () {
      if (_disposed) {
        return;
      }
      toastVisible = false;
      notifyListeners();
    });
  }

  @override
  void dispose() {
    _disposed = true;
    WidgetsBinding.instance.removeObserver(this);
    _poll?.cancel();
    _toastTimer?.cancel();
    searchController.dispose();
    relaySecretController.dispose();
    checkoutConfirmSecretController.dispose();
    super.dispose();
  }
}
