import 'package:flutter/material.dart';

import '../tokens.dart';

class PillSwitch extends StatelessWidget {
  const PillSwitch({
    super.key,
    required this.value,
    required this.onChanged,
  });

  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => onChanged(!value),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.ease,
        width: 46,
        height: 28,
        decoration: BoxDecoration(
          color: value ? RColors.purple : RColors.switchOff,
          borderRadius: BorderRadius.circular(RRadii.pill),
        ),
        child: AnimatedAlign(
          duration: const Duration(milliseconds: 200),
          curve: const Cubic(0.3, 0.8, 0.3, 1.0),
          alignment: value ? Alignment.centerRight : Alignment.centerLeft,
          child: Padding(
            padding: const EdgeInsets.all(3),
            child: Container(
              width: 22,
              height: 22,
              decoration: const BoxDecoration(
                color: Color(0xFFFFFFFF),
                shape: BoxShape.circle,
                boxShadow: RShadow.knob,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
