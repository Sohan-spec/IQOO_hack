import 'package:owner_app/api/python_client.dart';

import 'models.dart';

List<Payment> paymentsFromSnapshot(Snapshot snap) {
  final confirmed = <Payment>[];
  final seen = <String>{};
  for (final row in snap.recentMatches) {
    final id = row['session_id']?.toString() ?? '';
    if (id.isEmpty || seen.contains(id)) {
      continue;
    }
    seen.add(id);
    confirmed.add(_fromMatch(row));
  }
  final pending = <Payment>[];
  for (final row in snap.pending) {
    final id = row['session_id']?.toString() ?? '';
    if (id.isEmpty || seen.contains(id)) {
      continue;
    }
    seen.add(id);
    pending.add(_fromPending(row));
  }
  return [...pending, ...confirmed];
}

({num total, int count}) todayTotals(Snapshot snap) {
  var total = 0.0;
  var count = 0;
  for (final row in snap.recentMatches) {
    final iso = row['matched_at']?.toString() ?? row['at']?.toString() ?? '';
    if (!_isLocalToday(iso)) {
      continue;
    }
    total += _parseAmount(row['amount']);
    count += 1;
  }
  return (total: total, count: count);
}

String relativeFromSeconds(int seconds) {
  final s = seconds < 0 ? 0 : seconds;
  if (s < 60) {
    return 'Just now';
  }
  final minutes = s ~/ 60;
  if (minutes == 1) {
    return '1 min ago';
  }
  return '$minutes min ago';
}

String relativeFromIso(String iso) {
  final when = _parseLocal(iso);
  if (when == null) {
    return 'Just now';
  }
  return relativeFromSeconds(DateTime.now().difference(when).inSeconds);
}

String clockFromIso(String iso) {
  final when = _parseLocal(iso);
  if (when == null) {
    return '';
  }
  final period = when.hour >= 12 ? 'PM' : 'AM';
  var hour = when.hour % 12;
  if (hour == 0) {
    hour = 12;
  }
  final hh = hour.toString().padLeft(2, '0');
  final mm = when.minute.toString().padLeft(2, '0');
  return '$hh:$mm $period';
}

String groupFromIso(String iso) {
  final when = _parseLocal(iso);
  if (when == null) {
    return 'today';
  }
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final day = DateTime(when.year, when.month, when.day);
  if (day == today) {
    return 'today';
  }
  return 'yesterday';
}

String refFromSessionId(String sessionId) {
  if (sessionId.length <= 12) {
    return sessionId;
  }
  return sessionId.substring(sessionId.length - 12);
}

Payment _fromPending(Map<String, dynamic> row) {
  final id = row['session_id']?.toString() ?? '';
  final created = row['created_at']?.toString() ?? '';
  final elapsed = (row['elapsed_seconds'] is num)
      ? (row['elapsed_seconds'] as num).toInt()
      : int.tryParse(row['elapsed_seconds']?.toString() ?? '') ?? 0;
  return Payment(
    id: id,
    name: row['customer_name']?.toString() ?? '',
    amount: _parseAmount(row['amount']),
    status: PayStatus.pending,
    group: groupFromIso(created),
    clock: clockFromIso(created),
    relative: relativeFromSeconds(elapsed),
    ref: refFromSessionId(id),
    email: row['customer_email']?.toString(),
    phone: row['customer_phone']?.toString(),
  );
}

Payment _fromMatch(Map<String, dynamic> row) {
  final id = row['session_id']?.toString() ?? '';
  final matched = row['matched_at']?.toString() ?? row['at']?.toString() ?? '';
  return Payment(
    id: id,
    name: row['customer_name']?.toString() ?? '',
    amount: _parseAmount(row['amount']),
    status: PayStatus.successful,
    group: groupFromIso(matched),
    clock: clockFromIso(matched),
    relative: relativeFromIso(matched),
    ref: refFromSessionId(id),
    email: row['customer_email']?.toString(),
    phone: row['customer_phone']?.toString(),
  );
}

num _parseAmount(Object? value) {
  if (value is num) {
    return value;
  }
  return num.tryParse(value?.toString() ?? '') ?? 0;
}

DateTime? _parseLocal(String iso) {
  if (iso.isEmpty) {
    return null;
  }
  try {
    return DateTime.parse(iso).toLocal();
  } on FormatException {
    return null;
  }
}

bool _isLocalToday(String iso) {
  final when = _parseLocal(iso);
  if (when == null) {
    return false;
  }
  final now = DateTime.now();
  return when.year == now.year && when.month == now.month && when.day == now.day;
}
