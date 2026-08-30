import 'package:flutter_test/flutter_test.dart';
import 'package:owner_app/api/python_client.dart';
import 'package:owner_app/demo_ui/mapping.dart';
import 'package:owner_app/demo_ui/models.dart';

void main() {
  test('money groups the integer part and shows paise only when non-zero', () {
    expect(money(0), '₹0');
    expect(money(850), '₹850');
    expect(money(1200), '₹1,200');
    expect(money(12450), '₹12,450');
    expect(money(100000), '₹1,00,000');
    expect(money(150.5), '₹150.50');
    expect(money(150.00), '₹150');
    expect(money(-1200), '-₹1,200');
  });

  test('relativeFromSeconds uses just now then whole minutes', () {
    expect(relativeFromSeconds(0), 'Just now');
    expect(relativeFromSeconds(59), 'Just now');
    expect(relativeFromSeconds(60), '1 min ago');
    expect(relativeFromSeconds(125), '2 min ago');
  });

  test('clockFromIso formats local 12-hour time', () {
    expect(clockFromIso(DateTime(2026, 8, 29, 10, 24).toIso8601String()), '10:24 AM');
    expect(clockFromIso(DateTime(2026, 8, 29, 0, 5).toIso8601String()), '12:05 AM');
    expect(clockFromIso(DateTime(2026, 8, 29, 12, 0).toIso8601String()), '12:00 PM');
  });

  test('groupFromIso buckets today, yesterday, and older as yesterday', () {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day, 9);
    final yesterday = today.subtract(const Duration(days: 1));
    final older = today.subtract(const Duration(days: 5));
    expect(groupFromIso(today.toIso8601String()), 'today');
    expect(groupFromIso(yesterday.toIso8601String()), 'yesterday');
    expect(groupFromIso(older.toIso8601String()), 'yesterday');
  });

  test('paymentsFromSnapshot maps pending and confirmed and de-duplicates', () {
    final now = DateTime.now();
    final todayIso = now.toUtc().toIso8601String();
    final snap = Snapshot.fromJson({
      'pending': [
        {
          'session_id': 'sess-pending-only',
          'customer_name': 'Rahul Sharma',
          'amount': '850.00',
          'created_at': todayIso,
          'elapsed_seconds': 5,
          'customer_phone': '9876543210',
          'customer_email': 'rahul@example.com',
        },
        {
          'session_id': 'sess-dup',
          'customer_name': 'Dup',
          'amount': '10.00',
          'created_at': todayIso,
          'elapsed_seconds': 1,
        },
      ],
      'recent_matches': [
        {
          'session_id': 'sess-dup',
          'customer_name': 'Dup',
          'amount': '10.00',
          'matched_at': todayIso,
        },
        {
          'session_id': 'abcdefghijklmnopqrstuvwxyz',
          'customer_name': 'Karan Mehta',
          'amount': '150.50',
          'matched_at': todayIso,
          'customer_phone': '9108234562',
        },
      ],
      'recent_credits': <Object>[],
      'server': {'bind': '0.0.0.0:8787'},
    });

    final payments = paymentsFromSnapshot(snap);
    expect(payments.map((p) => p.id).toList(), [
      'sess-pending-only',
      'sess-dup',
      'abcdefghijklmnopqrstuvwxyz',
    ]);
    expect(payments[0].status, PayStatus.pending);
    expect(payments[0].name, 'Rahul Sharma');
    expect(payments[0].amount, 850);
    expect(payments[0].phone, '9876543210');
    expect(payments[0].email, 'rahul@example.com');
    expect(payments[0].ref, 'pending-only');
    expect(payments[1].status, PayStatus.successful);
    expect(payments[2].amount, 150.5);
    expect(payments[2].phone, '9108234562');
    expect(payments[2].ref, 'opqrstuvwxyz');
    expect(money(payments[2].amount), '₹150.50');
  });

  test('todayTotals sums only local-today matches', () {
    final now = DateTime.now();
    final todayIso = DateTime(now.year, now.month, now.day, 11).toUtc().toIso8601String();
    final yesterdayIso =
        DateTime(now.year, now.month, now.day).subtract(const Duration(days: 1)).toUtc().toIso8601String();
    final snap = Snapshot.fromJson({
      'pending': <Object>[],
      'recent_matches': [
        {
          'session_id': 'a',
          'customer_name': 'A',
          'amount': '100.50',
          'matched_at': todayIso,
        },
        {
          'session_id': 'b',
          'customer_name': 'B',
          'amount': '20',
          'matched_at': todayIso,
        },
        {
          'session_id': 'c',
          'customer_name': 'C',
          'amount': '999',
          'matched_at': yesterdayIso,
        },
      ],
      'recent_credits': <Object>[],
    });
    final totals = todayTotals(snap);
    expect(totals.count, 2);
    expect(totals.total, 120.5);
  });

  test('todayTotals de-duplicates the same session_id', () {
    final now = DateTime.now();
    final todayIso = DateTime(now.year, now.month, now.day, 11).toUtc().toIso8601String();
    final snap = Snapshot.fromJson({
      'pending': <Object>[],
      'recent_matches': [
        {
          'session_id': 'demo-4562-349',
          'customer_name': 'SOHAN REDDY P',
          'amount': '349.00',
          'matched_at': todayIso,
        },
        {
          'session_id': 'demo-4562-349',
          'customer_name': 'SOHAN REDDY P',
          'amount': '349.00',
          'matched_at': todayIso,
        },
      ],
      'recent_credits': <Object>[],
    });
    final totals = todayTotals(snap);
    expect(totals.count, 1);
    expect(totals.total, 349);
  });
}
