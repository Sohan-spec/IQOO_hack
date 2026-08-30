import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_app/api/python_client.dart';
import 'package:owner_app/demo_ui/demo_app.dart';
import 'package:owner_app/demo_ui/models.dart';
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
        case 'relayConnected':
          return false;
        case 'relayMerchantId':
          return '';
        case 'relaySecretConfigured':
          return false;
        case 'relaySecret':
          return '';
        case 'checkoutConfirmSecretConfigured':
          return false;
        case 'checkoutConfirmSecret':
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

Future<void> _disposeApp(WidgetTester tester) async {
  await tester.pumpWidget(const SizedBox());
  await tester.pump();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Snapshot keeps default_callback_url from the backend', () {
    final snapshot = Snapshot.fromJson({
      'pending': <Object>[],
      'recent_credits': <Object>[],
      'recent_matches': <Object>[],
      'default_callback_url': 'http://storefront.example/confirm',
      'server': {'bind': '0.0.0.0:8787'},
    });
    expect(snapshot.defaultCallbackUrl, 'http://storefront.example/confirm');
    expect(Snapshot.fromJson({}).defaultCallbackUrl, '');
  });

  testWidgets('operator screen loads', (WidgetTester tester) async {
    _mockDevice(tester, accessGranted: false);
    await tester.pumpWidget(const RelayOwnerApp());
    expect(find.text('Relay owner'), findsOneWidget);
    await _disposeApp(tester);
  });

  testWidgets('access off blocks pending and confirm', (WidgetTester tester) async {
    _mockDevice(tester, accessGranted: false);
    await _pumpOperator(tester);
    expect(find.text('Notification access required'), findsOneWidget);
    expect(find.text('Open notification access'), findsOneWidget);
    expect(find.text('Pending'), findsNothing);
    expect(find.text('Confirm'), findsNothing);
    expect(find.text('Credit events'), findsNothing);
    await _disposeApp(tester);
  });

  testWidgets('access on shows pending section', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
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
    await _disposeApp(tester);
  });

  testWidgets('pretty UI gates when notification access is off', (WidgetTester tester) async {
    _mockDevice(tester, accessGranted: false);
    await tester.pumpWidget(const DemoApp());
    await tester.pump();
    expect(find.text('Notification access required'), findsOneWidget);
    await _disposeApp(tester);
  });

  testWidgets('confirmAutoOn starts true and cannot be turned off', (
    WidgetTester tester,
  ) async {
    final controller = DemoController();
    expect(controller.confirmAutoOn, isTrue);
    controller.toggleConfirmAuto();
    expect(controller.confirmAutoOn, isTrue);
    expect(
      controller.toastMessage,
      'Auto-confirm is always on. Incoming credits are matched without a tap.',
    );
    controller.dispose();
  });

  testWidgets('pretty UI home shows after notification access is granted', (WidgetTester tester) async {
    _mockDevice(tester, accessGranted: true);
    await tester.pumpWidget(const DemoApp());
    var visible = false;
    for (var i = 0; i < 40; i++) {
      await tester.pump(const Duration(milliseconds: 50));
      if (find.text('Total received today').evaluate().isNotEmpty &&
          find.text('Notification access required').evaluate().isEmpty) {
        visible = true;
        break;
      }
    }
    expect(visible, isTrue);
    expect(find.text('Total received today'), findsOneWidget);
    expect(find.text('Nothing waiting. New payments show up here.'), findsOneWidget);
    await _disposeApp(tester);
  });
}

