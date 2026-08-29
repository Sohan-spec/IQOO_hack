import 'package:flutter/material.dart';

import '../models.dart';
import '../tokens.dart';

class ConfirmSheet extends StatelessWidget {
  const ConfirmSheet({
    super.key,
    required this.payment,
    required this.onConfirm,
    required this.onReject,
  });

  final Payment payment;
  final VoidCallback onConfirm;
  final VoidCallback onReject;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 26),
      decoration: const BoxDecoration(
        color: RColors.cardBg,
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(RRadii.sheet),
        ),
        boxShadow: RShadow.sheet,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 38,
              height: 4,
              margin: const EdgeInsets.only(bottom: 18),
              decoration: BoxDecoration(
                color: RColors.switchOff,
                borderRadius: BorderRadius.circular(RRadii.pill),
              ),
            ),
          ),
          const Text('Confirm payment', style: RText.sheetTitle),
          const SizedBox(height: 5),
          const Padding(
            padding: EdgeInsets.only(bottom: 20),
            child: Text(
              'Your phone detected this payment. Confirm it to release the order.',
              style: RText.sheetSub,
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Text(money(payment.amount), style: RText.sheetBig),
          ),
          _Kv(label: 'From', value: payment.name),
          _Kv(label: 'Detected', value: payment.relative),
          _Kv(label: 'UPI reference', value: payment.ref ?? ''),
          Padding(
            padding: const EdgeInsets.only(top: 22),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final rejectW = constraints.maxWidth * 0.38;
                return Row(
                  children: [
                    SizedBox(
                      width: rejectW,
                      child: _SheetButton(
                        label: 'Reject',
                        background: RColors.ghostBtnBg,
                        foreground: RColors.ghostBtnText,
                        onTap: onReject,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _SheetButton(
                        label: 'Confirm payment',
                        background: RColors.purple,
                        foreground: const Color(0xFFFFFFFF),
                        onTap: onConfirm,
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _Kv extends StatelessWidget {
  const _Kv({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 11),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: RText.kvKey),
          Flexible(
            child: Text(
              value,
              style: RText.kvValue,
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }
}

class _SheetButton extends StatelessWidget {
  const _SheetButton({
    required this.label,
    required this.background,
    required this.foreground,
    required this.onTap,
  });

  final String label;
  final Color background;
  final Color foreground;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 16),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(RRadii.button),
        ),
        child: Text(
          label,
          style: RText.btn.copyWith(color: foreground),
        ),
      ),
    );
  }
}
