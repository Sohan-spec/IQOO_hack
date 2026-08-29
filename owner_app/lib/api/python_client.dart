import 'package:http/http.dart' as http;
import 'dart:convert';

const pythonBase = 'http://127.0.0.1:8787';

class Snapshot {
  Snapshot({
    required this.pending,
    required this.recentCredits,
    required this.recentMatches,
    required this.bind,
  });

  final List<Map<String, dynamic>> pending;
  final List<Map<String, dynamic>> recentCredits;
  final List<Map<String, dynamic>> recentMatches;
  final String bind;

  factory Snapshot.fromJson(Map<String, dynamic> json) {
    return Snapshot(
      pending: _maps(json['pending']),
      recentCredits: _maps(json['recent_credits']),
      recentMatches: _maps(json['recent_matches']),
      bind: (json['server'] is Map ? json['server']['bind'] : null)?.toString() ?? '0.0.0.0:8787',
    );
  }

  static List<Map<String, dynamic>> _maps(dynamic value) {
    if (value is! List) {
      return [];
    }
    return value.whereType<Map>().map((row) => Map<String, dynamic>.from(row)).toList();
  }
}

class PythonClient {
  Future<Snapshot> snapshot() async {
    final response = await http.get(Uri.parse('$pythonBase/v1/internal/snapshot'));
    if (response.statusCode != 200) {
      throw StateError('snapshot ${response.statusCode}');
    }
    return Snapshot.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<void> manualConfirm(String sessionId) async {
    final response = await http.post(
      Uri.parse('$pythonBase/v1/internal/transactions/$sessionId/confirm'),
    );
    if (response.statusCode != 200) {
      throw StateError('confirm ${response.statusCode}: ${response.body}');
    }
  }

  Future<void> setDefaultCallbackUrl(String url) async {
    final response = await http.post(
      Uri.parse('$pythonBase/v1/internal/settings'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'default_callback_url': url}),
    );
    if (response.statusCode != 200) {
      throw StateError('settings ${response.statusCode}: ${response.body}');
    }
  }
}
