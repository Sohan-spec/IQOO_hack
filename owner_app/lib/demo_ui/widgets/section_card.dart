import 'package:flutter/material.dart';

import '../tokens.dart';

class SectionCard extends StatelessWidget {
  const SectionCard({
    super.key,
    required this.child,
    this.padding,
    this.clip = false,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final bool clip;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding,
      clipBehavior: clip ? Clip.antiAlias : Clip.none,
      decoration: BoxDecoration(
        color: RColors.cardBg,
        borderRadius: BorderRadius.circular(RRadii.card),
        border: Border.all(color: RColors.cardLine, width: 1),
        boxShadow: RShadow.card,
      ),
      child: child,
    );
  }
}
