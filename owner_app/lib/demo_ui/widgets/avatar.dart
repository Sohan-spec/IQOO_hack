import 'package:flutter/material.dart';

import '../icons.dart';
import '../models.dart';
import '../tokens.dart';

class PaymentAvatar extends StatelessWidget {
  const PaymentAvatar({
    super.key,
    required this.status,
    required this.name,
  });

  final PayStatus status;
  final String name;

  @override
  Widget build(BuildContext context) {
    final Color bg;
    final Widget child;
    switch (status) {
      case PayStatus.successful:
        bg = RColors.greenBg;
        child = const RSvg(RIcons.rowCheck, width: 19, height: 19);
      case PayStatus.failed:
        bg = RColors.redBg;
        child = const RSvg(RIcons.rowCross, width: 17, height: 17);
      case PayStatus.pending:
        bg = RColors.purpleTint;
        child = Text(initials(name), style: RText.avatarInitials);
    }
    return Container(
      width: 34,
      height: 34,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: bg,
        shape: BoxShape.circle,
      ),
      child: child,
    );
  }
}
