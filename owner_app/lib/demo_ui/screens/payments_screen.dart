import 'package:flutter/material.dart';

import '../icons.dart';
import '../models.dart';
import '../tokens.dart';
import '../widgets/app_top_bar.dart';
import '../widgets/filter_chips.dart';
import '../widgets/payment_row.dart';
import '../widgets/search_field.dart';
import '../widgets/section_card.dart';

class PaymentsScreen extends StatelessWidget {
  const PaymentsScreen({super.key, required this.controller});

  final DemoController controller;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        final items = controller.filteredPayments;
        final today = items.where((p) => p.group == 'today').toList();
        final yesterday = items.where((p) => p.group == 'yesterday').toList();
        var firstGroup = true;

        Widget dateLabel(String text, {required bool first}) {
          return Padding(
            padding: EdgeInsets.fromLTRB(0, first ? 6 : 12, 0, 2),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(text, style: RText.dateLabel),
            ),
          );
        }

        final listChildren = <Widget>[];
        if (items.isEmpty) {
          listChildren.add(
            const Padding(
              padding: EdgeInsets.fromLTRB(0, 14, 0, 16),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('No payments here yet.', style: RText.empty),
              ),
            ),
          );
        } else {
          if (today.isNotEmpty) {
            listChildren.add(dateLabel('Today', first: firstGroup));
            firstGroup = false;
            for (final p in today) {
              listChildren.add(
                PaymentRow(
                  payment: p,
                  variant: PaymentRowVariant.payments,
                  onTap: p.status == PayStatus.pending
                      ? () => controller.openSheet(p)
                      : null,
                ),
              );
            }
          }
          if (yesterday.isNotEmpty) {
            listChildren.add(dateLabel('Yesterday', first: firstGroup));
            for (final p in yesterday) {
              listChildren.add(
                PaymentRow(
                  payment: p,
                  variant: PaymentRowVariant.payments,
                  onTap: p.status == PayStatus.pending
                      ? () => controller.openSheet(p)
                      : null,
                ),
              );
            }
          }
        }

        return SingleChildScrollView(
          padding: RSpace.screen,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AppTopBar(onSettings: controller.openSettings),
              const Padding(
                padding: EdgeInsets.only(bottom: 16),
                child: Text('Payments', style: RText.pageTitle),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: Row(
                  children: [
                    Expanded(
                      child: SearchField(
                        controller: controller.searchController,
                        onChanged: controller.setQuery,
                      ),
                    ),
                    const SizedBox(width: 10),
                    RIconButton(
                      svg: RIcons.filter,
                      size: 18,
                      onTap: () => controller.showToast(
                        'Use the tabs to filter by status',
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: FilterChips(
                  selected: controller.chipFilter,
                  onSelected: controller.setChip,
                ),
              ),
              SectionCard(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Column(children: listChildren),
              ),
            ],
          ),
        );
      },
    );
  }
}
