// Keep standard Flutter Material widgets compatible with the existing app SDK range.
// ignore_for_file: deprecated_member_use
import 'package:flutter/material.dart';

import 'app/controller.dart';
import 'app/views.dart';
import 'core/api.dart';
import 'core/storage.dart';
import 'core/platform_database.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final controller = AppController(
    local: await openPlatformDatabase(),
    vault: SecureVault(),
    api: GameApi(
      const String.fromEnvironment(
        'BACKEND_URL',
        defaultValue: 'http://10.0.2.2:8000',
      ),
    ),
  );
  runApp(ChematApp(controller: controller));
  await controller.initialize();
}

class ChematApp extends StatelessWidget {
  final AppController controller;
  const ChematApp({super.key, required this.controller});
  @override
  Widget build(BuildContext context) =>
      MaterialApp(title: 'CHEMa’t', home: AppView(controller));
}
