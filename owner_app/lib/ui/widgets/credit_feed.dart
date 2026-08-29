import 'package:flutter/material.dart';

class CreditFeed extends StatelessWidget {
  const CreditFeed({super.key, required this.credits});

  final List<Map<String, dynamic>> credits;

  @override
  Widget build(BuildContext context) {
    if (credits.isEmpty) {
      return const ListTile(
        title: Text('No credit events yet'),
        subtitle: Text('PhonePe credits will appear here as they are parsed.'),
      );
    }
    return Column(
      children: [
        for (final row in credits.take(8))
          ListTile(
            dense: true,
            title: Text('₹${row['amount']}  ${row['payer_name']}'),
            subtitle: Text('${row['title']}  ${row['text']}'),
          ),
      ],
    );
  }
}
