import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_app/main.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('operator screen loads', (WidgetTester tester) async {
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      const MethodChannel('com.relay.owner/device'),
      (call) async {
        switch (call.method) {
          case 'notificationAccessGranted':
            return false;
          case 'getInterruptionFilter':
            return 1;
          case 'batteryOptimizationIgnored':
            return true;
          default:
            return null;
        }
      },
    );
    await tester.pumpWidget(const RelayOwnerApp());
    expect(find.text('Relay owner'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });
}
