import 'package:flutter/material.dart';

import '../models.dart';
import '../tokens.dart';

class FilterChips extends StatelessWidget {
  const FilterChips({
    super.key,
    required this.selected,
    required this.onSelected,
  });

  final PayStatus? selected;
  final ValueChanged<PayStatus?> onSelected;

  static const _items = <(PayStatus?, String)>[
    (null, 'All'),
    (PayStatus.pending, 'Pending'),
    (PayStatus.successful, 'Successful'),
    (PayStatus.failed, 'Failed'),
  ];

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      clipBehavior: Clip.none,
      child: Row(
        children: [
          for (var i = 0; i < _items.length; i++) ...[
            if (i > 0) const SizedBox(width: 8),
            _Chip(
              label: _items[i].$2,
              selected: selected == _items[i].$1,
              onTap: () => onSelected(_items[i].$1),
            ),
          ],
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? RColors.purpleTint : Colors.transparent,
          borderRadius: BorderRadius.circular(RRadii.chip),
        ),
        child: Text(label, style: selected ? RText.chipOn : RText.chip),
      ),
    );
  }
}
