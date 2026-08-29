import 'package:flutter/material.dart';

import 'demo_shell.dart';
import 'tokens.dart';

class DemoApp extends StatelessWidget {
  const DemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: RColors.bg,
        fontFamily: 'Manrope',
        colorScheme: ColorScheme.fromSeed(
          seedColor: RColors.purple,
          brightness: Brightness.light,
        ).copyWith(primary: RColors.purple, surface: RColors.cardBg),
        splashFactory: NoSplash.splashFactory,
      ),
      home: const DemoShell(),
    );
  }
}
