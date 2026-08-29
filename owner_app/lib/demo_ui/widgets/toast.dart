import 'package:flutter/material.dart';

import '../icons.dart';
import '../tokens.dart';

class RToast extends StatelessWidget {
  const RToast({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: RColors.toastBg,
        borderRadius: BorderRadius.circular(RRadii.toast),
      ),
      child: Row(
        children: [
          const RSvg(RIcons.toastCheck, width: 18, height: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(message, style: RText.toast),
          ),
        ],
      ),
    );
  }
}
