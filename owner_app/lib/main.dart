import 'package:flutter/material.dart';
import 'package:owner_app/ui/operator_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const RelayOwnerApp());
}

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
