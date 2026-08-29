import 'package:flutter/material.dart';

import '../icons.dart';
import '../tokens.dart';

class SearchField extends StatelessWidget {
  const SearchField({
    super.key,
    required this.controller,
    required this.onChanged,
  });

  final TextEditingController controller;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 44,
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(
        color: RColors.search,
        borderRadius: BorderRadius.circular(RRadii.search),
      ),
      child: Row(
        children: [
          const RSvg(
            RIcons.search,
            width: 18,
            height: 18,
            color: RColors.placeholder,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: TextField(
              controller: controller,
              onChanged: onChanged,
              cursorColor: RColors.purple,
              style: RText.searchInput,
              textAlignVertical: TextAlignVertical.center,
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                isDense: true,
                border: InputBorder.none,
                contentPadding: EdgeInsets.zero,
                hintText: 'Search transactions',
                hintStyle: TextStyle(
                  fontFamily: 'Manrope',
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: RColors.placeholder,
                  letterSpacing: -0.30,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
