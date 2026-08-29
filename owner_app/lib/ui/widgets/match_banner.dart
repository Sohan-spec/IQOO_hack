import 'package:flutter/material.dart';

class MatchBanner extends StatelessWidget {
  const MatchBanner({super.key, required this.match});

  final Map<String, dynamic>? match;

  @override
  Widget build(BuildContext context) {
    if (match == null) {
      return const SizedBox.shrink();
    }
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.all(16),
      color: const Color(0xFF143D2C),
      child: Text(
        'MATCH  ${match!['customer_name']}  ₹${match!['amount']}\n'
        '${match!['source']} → ${match!['session_id']}',
        style: const TextStyle(color: Color(0xFF3DDC97), fontWeight: FontWeight.w600),
      ),
    );
  }
}
