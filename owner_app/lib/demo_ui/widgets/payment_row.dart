import 'package:flutter/material.dart';

import '../models.dart';
import '../tokens.dart';
import 'avatar.dart';

enum PaymentRowVariant { home, payments }

class PaymentRow extends StatelessWidget {
  const PaymentRow({
    super.key,
    required this.payment,
    required this.variant,
    this.onTap,
  });

  final Payment payment;
  final PaymentRowVariant variant;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final secondary = variant == PaymentRowVariant.home
        ? payment.relative
        : payment.clock;

    final row = Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          PaymentAvatar(status: payment.status, name: payment.name),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  payment.name,
                  style: RText.rowName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(secondary, style: RText.rowTime),
              ],
            ),
          ),
          const SizedBox(width: 16),
          if (variant == PaymentRowVariant.home)
            Text(money(payment.amount), style: RText.rowValue)
          else
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(money(payment.amount), style: RText.rowValue),
                const SizedBox(height: 4),
                Text(
                  payment.status.label,
                  style: RText.payStatus.copyWith(color: payment.status.color),
                ),
              ],
            ),
        ],
      ),
    );

    if (onTap == null) return row;
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: row,
    );
  }
}
