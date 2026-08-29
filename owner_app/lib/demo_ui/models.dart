import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

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
  });

  final String id;
  String name;
  int amount;
  PayStatus status;
  String group;
  String clock;
  String relative;
  String? ref;
}

String money(int n) {
  var s = n.abs().toString();
  if (s.length <= 3) return '₹$s';
  final last3 = s.substring(s.length - 3);
  s = s.substring(0, s.length - 3);
  final parts = <String>[last3];
  while (s.length > 2) {
    parts.insert(0, s.substring(s.length - 2));
    s = s.substring(0, s.length - 2);
  }
  if (s.isNotEmpty) parts.insert(0, s);
  return '₹${parts.join(',')}';
}

String initials(String name) {
  final chars = name
      .split(' ')
      .where((w) => w.isNotEmpty)
      .map((w) => w[0])
      .join()
      .toUpperCase();
  if (chars.length <= 2) return chars;
  return chars.substring(0, 2);
}

String nextRef() {
  final n = 400000000000 + (math.Random().nextDouble() * 500000000000).floor();
  return n.toString();
}

String nowClock() {
  final now = DateTime.now();
  final period = now.hour >= 12 ? 'PM' : 'AM';
  var hour = now.hour % 12;
  if (hour == 0) hour = 12;
  final hh = hour.toString().padLeft(2, '0');
  final mm = now.minute.toString().padLeft(2, '0');
  return '$hh:$mm $period';
}

List<Payment> seedPayments() {
  return [
    Payment(
      id: 'p1',
      name: 'Rahul Sharma',
      amount: 850,
      status: PayStatus.pending,
      group: 'today',
      clock: '10:24 AM',
      relative: '2 min ago',
      ref: nextRef(),
    ),
    Payment(
      id: 'r1',
      name: 'Karan Mehta',
      amount: 1200,
      status: PayStatus.successful,
      group: 'today',
      clock: '09:48 AM',
      relative: 'Just now',
    ),
    Payment(
      id: 'r2',
      name: 'Ananya Verma',
      amount: 450,
      status: PayStatus.successful,
      group: 'today',
      clock: '09:15 AM',
      relative: '8 min ago',
    ),
    Payment(
      id: 'p2',
      name: 'Ananya Verma',
      amount: 1150,
      status: PayStatus.pending,
      group: 'yesterday',
      clock: '07:30 PM',
      relative: '4 min ago',
      ref: nextRef(),
    ),
    Payment(
      id: 'r3',
      name: 'Rohit Singh',
      amount: 650,
      status: PayStatus.successful,
      group: 'yesterday',
      clock: '06:20 PM',
      relative: '21 min ago',
    ),
    Payment(
      id: 'f1',
      name: 'Neha Gupta',
      amount: 800,
      status: PayStatus.failed,
      group: 'yesterday',
      clock: '05:45 PM',
      relative: '34 min ago',
    ),
  ];
}

class DemoController extends ChangeNotifier {
  DemoController() : payments = seedPayments();

  final List<Payment> payments;
  final searchController = TextEditingController();

  int total = 12450;
  int count = 14;
  int currentTab = 0;
  int lastTab = 0;
  bool showingSettings = false;
  PayStatus? chipFilter;
  String searchQuery = '';
  bool notifAccessOn = true;
  bool confirmAutoOn = false;
  bool soundOn = true;

  Payment? sheetPayment;
  bool sheetOpen = false;

  String toastMessage = 'Payment confirmed';
  bool toastVisible = false;
  Timer? _toastTimer;

  List<Payment> get pending =>
      payments.where((p) => p.status == PayStatus.pending).toList();

  List<Payment> get successful =>
      payments.where((p) => p.status == PayStatus.successful).toList();

  List<Payment> get filteredPayments {
    final q = searchQuery.toLowerCase();
    return payments.where((p) {
      if (chipFilter != null && p.status != chipFilter) return false;
      if (q.isNotEmpty && !p.name.toLowerCase().contains(q)) return false;
      return true;
    }).toList();
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
    if (!sheetOpen) return;
    sheetOpen = false;
    notifyListeners();
  }

  void confirmPayment() {
    final p = sheetPayment;
    if (p == null) return;
    p.status = PayStatus.successful;
    p.relative = 'Just now';
    p.clock = nowClock();
    p.group = 'today';
    payments.remove(p);
    payments.insert(0, p);
    total += p.amount;
    count += 1;
    closeSheet();
    showToast('Payment confirmed');
  }

  void rejectPayment() {
    final p = sheetPayment;
    if (p == null) return;
    p.status = PayStatus.failed;
    closeSheet();
    showToast('Payment rejected');
  }

  void toggleConfirmAuto() {
    confirmAutoOn = !confirmAutoOn;
    notifyListeners();
  }

  void toggleNotifAccess() {
    notifAccessOn = !notifAccessOn;
    notifyListeners();
  }

  void toggleSound() {
    soundOn = !soundOn;
    notifyListeners();
  }

  void showToast(String msg) {
    toastMessage = msg;
    toastVisible = true;
    notifyListeners();
    _toastTimer?.cancel();
    _toastTimer = Timer(const Duration(milliseconds: 2200), () {
      toastVisible = false;
      notifyListeners();
    });
  }

  @override
  void dispose() {
    _toastTimer?.cancel();
    searchController.dispose();
    super.dispose();
  }
}
