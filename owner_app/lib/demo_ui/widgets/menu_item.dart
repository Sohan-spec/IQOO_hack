import 'package:flutter/material.dart';

import '../icons.dart';
import '../tokens.dart';

class MenuItem extends StatelessWidget {
  const MenuItem({
    super.key,
    this.iconSvg,
    required this.title,
    this.subtitle,
    this.subtitleOk = false,
    this.danger = false,
    this.showChevron = true,
    this.trailing,
    this.onTap,
  });

  final String? iconSvg;
  final String title;
  final String? subtitle;
  final bool subtitleOk;
  final bool danger;
  final bool showChevron;
  final Widget? trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final row = Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          if (iconSvg != null) ...[
            Container(
              width: 36,
              height: 36,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: danger ? RColors.redBg : RColors.purpleTint,
                borderRadius: BorderRadius.circular(RRadii.menuIcon),
              ),
              child: RSvg(
                iconSvg!,
                width: 18,
                height: 18,
                color: danger ? RColors.red : RColors.purple,
              ),
            ),
            const SizedBox(width: 14),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: danger ? RText.miTitleDanger : RText.miTitle,
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    subtitle!,
                    style: subtitleOk ? RText.miSubOk : RText.miSub,
                  ),
                ],
              ],
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: 14),
            trailing!,
          ] else if (showChevron) ...[
            const SizedBox(width: 14),
            const RSvg(
              RIcons.chevronRight,
              width: 18,
              height: 18,
              color: RColors.chevron,
            ),
          ],
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
