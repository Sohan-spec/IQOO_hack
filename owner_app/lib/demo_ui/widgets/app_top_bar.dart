import 'package:flutter/material.dart';

import '../icons.dart';
import '../tokens.dart';

class RIconButton extends StatelessWidget {
  const RIconButton({
    super.key,
    required this.svg,
    required this.onTap,
    this.size = 21,
  });

  final String svg;
  final VoidCallback onTap;
  final double size;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: RColors.cardBg,
          borderRadius: BorderRadius.circular(RRadii.iconBtn),
          border: Border.all(color: RColors.iconBtnBorder),
        ),
        child: RSvg(svg, width: size, height: size),
      ),
    );
  }
}

class AppTopBar extends StatelessWidget {
  const AppTopBar({super.key, required this.onSettings});

  final VoidCallback onSettings;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(0, 6, 0, 18),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Image.asset(
            'assets/images/logo-full.png',
            height: 32,
            filterQuality: FilterQuality.medium,
          ),
          RIconButton(svg: RIcons.gear, onTap: onSettings),
        ],
      ),
    );
  }
}
