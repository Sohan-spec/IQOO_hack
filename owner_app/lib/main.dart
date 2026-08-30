import 'package:flutter/material.dart';
import 'package:owner_app/demo_ui/demo_app.dart';
import 'package:owner_app/ui/operator_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const DemoApp());
}

/// Debug/operator UI. Kept so existing widget tests and a fallback entry still compile.
class RelayOwnerApp extends StatelessWidget {
  const RelayOwnerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Relay owner',
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0E1116),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF3DDC97),
          secondary: Color(0xFF3DDC97),
          error: Color(0xFFE85D4C),
        ),
      ),
      home: const OperatorScreen(),
    );
  }
}
