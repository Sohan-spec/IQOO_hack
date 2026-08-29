import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_app/main.dart';

void _mockDevice(WidgetTester tester, {required bool accessGranted}) {
  tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
    const MethodChannel('com.relay.owner/device'),
    (call) async {
      switch (call.method) {
        case 'notificationAccessGranted':
          return accessGranted;
        case 'getInterruptionFilter':
          return 1;
        case 'batteryOptimizationIgnored':
          return true;
        case 'runSetupPrompts':
          return null;
        case 'getDefaultCallbackUrl':
          return '';
        default:
          return null;
      }
    },
  );
}

Future<void> _pumpOperator(WidgetTester tester) async {
  await tester.pumpWidget(const RelayOwnerApp());
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 200));
}

Future<void> _disposeOperator(WidgetTester tester) async {
  await tester.pumpWidget(const SizedBox());
  await tester.pump();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('operator screen loads', (WidgetTester tester) async {
    _mockDevice(tester, accessGranted: false);
    await tester.pumpWidget(const RelayOwnerApp());
    expect(find.text('Relay owner'), findsOneWidget);
    await _disposeOperator(tester);
  });

  testWidgets('access off blocks pending and confirm', (WidgetTester tester) async {
    _mockDevice(tester, accessGranted: false);
    await _pumpOperator(tester);
    expect(find.text('Notification access required'), findsOneWidget);
    expect(
      find.text('Grant notification access before anything else is usable. Tap to open system settings.'),
      findsOneWidget,
    );
    expect(find.text('Pending'), findsNothing);
    expect(find.text('Confirm'), findsNothing);
    expect(find.text('Credit events'), findsNothing);
    await _disposeOperator(tester);
  });

  testWidgets('access on shows pending section', (WidgetTester tester) async {
    _mockDevice(tester, accessGranted: true);
    await tester.pumpWidget(const RelayOwnerApp());
    var visible = false;
    for (var i = 0; i < 40; i++) {
      await tester.pump(const Duration(milliseconds: 50));
      if (find.text('Pending').evaluate().isNotEmpty) {
        visible = true;
        break;
      }
    }
    expect(visible, isTrue);
    expect(find.text('Pending'), findsOneWidget);
    await _disposeOperator(tester);
  });
}
