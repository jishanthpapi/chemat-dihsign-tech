// Diagnostic regression for the real-I/O test lifecycle, not a gameplay demonstration.
// ignore_for_file: deprecated_member_use
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:chemat/main.dart';
import 'package:chemat/app/controller.dart';
import 'package:chemat/core/api.dart';
import 'package:chemat/core/storage.dart';

import 'widget_test.dart' show TestVault;

void main() {
  const endpoint = String.fromEnvironment('LIVE_BACKEND');
  testWidgets(
    'two live clients release all asynchronous resources',
    skip: endpoint.isEmpty,
    (tester) async {
      HttpOverrides.global = null;
      sqfliteFfiInit();
      final clients = <AppController>[];
      await tester.runAsync(() async {
        final directory = await Directory.systemTemp.createTemp(
          'chemat-cleanup-probe-',
        );
        for (var i = 0; i < 2; i++) {
          final local = await LocalStore.open(
            filename: '${directory.path}/client-$i.db',
            factory: databaseFactoryFfi,
          );
          final c = AppController(
            local: local,
            vault: TestVault(),
            api: GameApi(endpoint),
          );
          await c.register(
            'cleanup-${DateTime.now().microsecondsSinceEpoch}-$i',
            endpoint,
          );
          await c.initialize();
          clients.add(c);
        }
        await clients[0].createLobby();
        await clients[1].join(clients[0].profile!.lobby!);
        await clients[0].lobbyAction('ready');
        await clients[1].lobbyAction('ready');
        await clients[0].lobbyAction('start');
        await clients[1].refresh();
        await Future<void>.delayed(const Duration(milliseconds: 500));
      });
      tester.view.physicalSize = const Size(1600, 1200);
      tester.view.devicePixelRatio = 1;
      await tester.pumpWidget(
        Row(
          textDirection: TextDirection.ltr,
          children: [
            for (final c in clients) Expanded(child: ChematApp(controller: c)),
          ],
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));
      expect(clients.every((c) => c.game != null), isTrue);
      await tester.runAsync(() async {
        for (final c in clients) {
          c.dispose();
        }
        for (final c in clients) {
          await c.local.database.close().timeout(const Duration(seconds: 5));
        }
      });
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      // Drain the WebSocket close-handshake deadline on the widget fake clock.
      await tester.pump(const Duration(seconds: 5));
      debugPrint('Cleanup probe final frame pumped');
    },
  );
}
