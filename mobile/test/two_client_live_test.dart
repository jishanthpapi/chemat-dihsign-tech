// End-user UI integration: no command, purchase, resource, score or result injection.
// ignore_for_file: deprecated_member_use
import 'dart:io';
import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:chemat/main.dart';
import 'package:chemat/app/controller.dart';
import 'package:chemat/core/api.dart';
import 'package:chemat/core/storage.dart';

class IsolatedVault implements CredentialVault {
  String? secret;
  @override
  Future<String?> read() async => secret;
  @override
  Future<void> write(String value) async {
    secret = value;
  }

  @override
  Future<void> clear() async {
    secret = null;
  }
}

void main() {
  final clients = <AppController>[];
  tearDown(() async {
    for (final c in clients) {
      if (!c.disposed) c.dispose();
    }
    clients.clear();
  });
  const endpoint = String.fromEnvironment('LIVE_BACKEND');
  const restartSignal = String.fromEnvironment('RESTART_SIGNAL');
  testWidgets(
    'two authenticated UI clients complete a real match',
    skip: endpoint.isEmpty,
    (tester) async {
      HttpOverrides.global = null;
      sqfliteFfiInit();
      final directory = await tester.runAsync(
        () => Directory.systemTemp.createTemp('chemat-ui-'),
      );
      await tester.runAsync(() async {
        final sdk = Platform.environment['FLUTTER_ROOT'] ?? '../.tools/flutter';
        final font = File(
          '$sdk/bin/cache/artifacts/material_fonts/roboto-regular.ttf',
        );
        if (await font.exists()) {
          final bytes = await font.readAsBytes();
          final loader = FontLoader('Roboto')
            ..addFont(Future.value(ByteData.view(bytes.buffer)));
          await loader.load();
        }
      });
      tester.view.physicalSize = const Size(1600, 1200);
      tester.view.devicePixelRatio = 1;
      for (var i = 0; i < 2; i++) {
        final c = await tester.runAsync(() async {
          final local = await LocalStore.open(
            filename: '${directory!.path}/client-$i.sqlite3',
            factory: databaseFactoryFfi,
          );
          final controller = AppController(
            local: local,
            vault: IsolatedVault(),
            api: GameApi(endpoint),
          );
          await controller.initialize();
          return controller;
        });
        clients.add(c!);
      }
      final capture = GlobalKey();
      await tester.pumpWidget(
        RepaintBoundary(
          key: capture,
          child: Row(
            textDirection: TextDirection.ltr,
            children: [
              for (var i = 0; i < 2; i++)
                Expanded(
                  child: KeyedSubtree(
                    key: ValueKey('client-$i'),
                    child: ChematApp(controller: clients[i]),
                  ),
                ),
            ],
          ),
        ),
      );
      Finder scoped(int i, Finder finder) => find.descendant(
        of: find.byKey(ValueKey('client-$i')),
        matching: finder,
      );
      Future<void> settle() async {
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 90)),
        );
        await tester.pump(const Duration(milliseconds: 100));
        for (var n = 0; n < 100 && clients.any((c) => c.busy); n++) {
          await tester.runAsync(
            () => Future<void>.delayed(const Duration(milliseconds: 30)),
          );
          await tester.pump(const Duration(milliseconds: 100));
        }
        await tester.pump(const Duration(milliseconds: 400));
      }

      Future<void> tap(int i, Finder finder) async {
        final target = scoped(i, finder);
        if (target.evaluate().isEmpty) {
          final scroll = scoped(i, find.byKey(const ValueKey('game-scroll')));
          if (scroll.evaluate().isNotEmpty) {
            // Return to the start with a real scroll gesture before seeking a lazy child.
            await tester.drag(scroll, const Offset(0, 50000));
            await tester.pump(const Duration(seconds: 1));
            await tester.scrollUntilVisible(
              target,
              500,
              scrollable: find
                  .descendant(of: scroll, matching: find.byType(Scrollable))
                  .first,
              maxScrolls: 100,
            );
          }
        }
        await Scrollable.ensureVisible(
          tester.element(target.first),
          alignment: 0.5,
        );
        await tester.pump(const Duration(milliseconds: 100));
        await tester.tap(target.first);
        await settle();
      }

      Future<void> press(int i, String key) =>
          tap(i, find.byKey(ValueKey(key)));
      Future<void> sync() async {
        for (var i = 0; i < 2; i++) {
          if (clients[i].game != null) await tap(i, find.text('Refresh state'));
        }
        await settle();
      }

      final suffix = DateTime.now().microsecondsSinceEpoch;
      for (var i = 0; i < 2; i++) {
        await tester.enterText(
          scoped(i, find.byKey(const ValueKey('username'))),
          'ui-$suffix-$i',
        );
        await press(i, 'register');
        expect(clients[i].profile, isNotNull, reason: clients[i].error);
      }
      expect(clients[0].id, isNot(clients[1].id));
      await press(0, 'create-lobby');
      final code = (tester.widget<Text>(
        scoped(0, find.byKey(const ValueKey('lobby-code'))),
      )).data!;
      await tester.enterText(
        scoped(1, find.byKey(const ValueKey('invite-code'))),
        code,
      );
      await press(1, 'join-lobby');
      // Poll through the app's normal timer, not direct API calls.
      await tester.pump(const Duration(seconds: 2));
      await settle();
      await press(0, 'ready');
      await press(1, 'ready');
      await tester.pump(const Duration(seconds: 2));
      await settle();
      await press(0, 'start-match');
      for (var n = 0; n < 60 && clients.any((c) => c.game == null); n++) {
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 100)),
        );
        await tester.pump(const Duration(milliseconds: 100));
      }
      await sync();
      expect(
        clients.every((c) => c.game != null),
        isTrue,
        reason: clients.map((c) => c.error).toString(),
      );
      final log = <Map<String, dynamic>>[];
      var reconnected = false;
      var turns = 0;
      while (!clients[0].game!.finished && turns < 800) {
        await sync();
        if (clients[0].game!.finished) break;
        if (turns == 10 && restartSignal.isNotEmpty) {
          await tester.runAsync(
            () => File(restartSignal).writeAsString('ready'),
          );
          var acknowledged = false;
          for (var n = 0; n < 200; n++) {
            acknowledged = (await tester.runAsync(
              () => File('$restartSignal.ack').exists(),
            ))!;
            if (acknowledged) break;
            await tester.runAsync(
              () => Future<void>.delayed(const Duration(milliseconds: 100)),
            );
            await tester.pump(const Duration(milliseconds: 200));
          }
          expect(
            acknowledged,
            isTrue,
            reason: 'Backend restart coordinator did not respond',
          );
          for (
            var n = 0;
            n < 100 && clients.any((c) => c.connection != 'Connected');
            n++
          ) {
            await tester.runAsync(
              () => Future<void>.delayed(const Duration(milliseconds: 100)),
            );
            await tester.pump(const Duration(milliseconds: 200));
          }
          await sync();
          expect(clients.every((c) => c.connection == 'Connected'), isTrue);
        }
        final current = clients[0].game!.current;
        final i = clients.indexWhere((c) => c.id == current);
        expect(i, greaterThanOrEqualTo(0));
        final c = clients[i];
        final g = c.game!;
        for (final other in clients) {
          final opponent =
              other.game!.state['players'][clients[1 - clients.indexOf(other)]
                      .id]
                  as Map;
          expect(opponent.containsKey('task'), isFalse);
          expect(opponent.containsKey('hand'), isFalse);
        }
        if (!reconnected && turns > 2) {
          // Transport fault only: no gameplay state or API command is injected.
          await tester.runAsync(() => clients[1].channel!.sink.close());
          await tester.pump(const Duration(seconds: 3));
          await settle();
          await sync();
          for (
            var n = 0;
            n < 100 && clients[1].connection != 'Connected';
            n++
          ) {
            await tester.runAsync(
              () => Future<void>.delayed(const Duration(milliseconds: 100)),
            );
            await tester.pump(const Duration(milliseconds: 200));
          }
          expect(clients[1].connection, 'Connected');
          reconnected = true;
        }
        final recipe = g.recipe;
        final required = <List<String>>[
          if (recipe != null) ...[
            for (final name in recipe['reactants']) ['reactant', name],
            for (final name in recipe['apparatus']) ['apparatus', name],
          ],
        ];
        bool owns(List<String> card) => c.game!.instances.values.any(
          (v) => v[0] == card[0] && v[1] == card[1],
        );
        if (g.phase == 'regular') {
          // Cooperative players may gift needed resources using ordinary proposal dialogs.
          for (final card in required.where((card) => !owns(card)).toList()) {
            final donor = 1 - i;
            final matching = clients[donor].game!.instances.entries
                .where((e) => e.value[0] == card[0] && e.value[1] == card[1])
                .toList();
            if (matching.isEmpty) continue;
            await press(donor, 'propose-trade');
            await tap(donor, find.byKey(const ValueKey('offer-target')));
            await tap(donor, find.text(c.id).last);
            await tap(
              donor,
              find.byKey(ValueKey('offer-${matching.first.key}')),
            );
            await press(donor, 'send-offer');
            await sync();
            final offers = c.game!.state['offers'] as Map;
            final key = offers.entries
                .lastWhere(
                  (e) =>
                      e.value['status'] == 'pending' &&
                      e.value['target'] == c.id,
                )
                .key;
            await press(i, 'accept-$key');
            await sync();
          }
          var purchases = 0;
          for (final kind in ['reactant', 'apparatus']) {
            while (required.any((card) => card[0] == kind && !owns(card)) &&
                (c.game!.player(c.id)['pesos'] as int) >
                    (recipe?['fee'] ?? 9) &&
                purchases < 100 &&
                ((c.game!.state['decks'][kind]['remaining'] as int) > 0 ||
                    (c.game!.state['decks'][kind]['discard'] as List)
                        .isNotEmpty)) {
              await press(i, 'buy-$kind');
              purchases++;
              expect(c.error, isNull, reason: c.error);
            }
          }
          await press(i, 'end_turn');
        } else if (g.phase == 'reaction') {
          if (recipe != null &&
              required.every(owns) &&
              (g.player(c.id)['pesos'] as int) >= recipe['fee']) {
            await press(i, 'scanner');
            final used = <String>{};
            for (final card in required) {
              final entry = c.game!.instances.entries.firstWhere(
                (e) =>
                    !used.contains(e.key) &&
                    e.value[0] == card[0] &&
                    e.value[1] == card[1],
              );
              used.add(entry.key);
              await tap(i, find.byKey(ValueKey('scan-${entry.key}')));
            }
            await press(i, 'submit-scan');
            expect(c.error, isNull, reason: c.error);
          }
          await press(i, 'end_reaction');
        } else {
          fail('Unexpected phase ${g.phase}');
        }
        log.add({
          'step': turns,
          'phase': g.phase,
          'player': i,
          'round': g.state['round'],
        });
        turns++;
        if (turns % 10 == 0) {
          debugPrint(
            'UI match progress: $turns opportunities, round ${g.state['round']}',
          );
        }
      }
      await sync();
      expect(
        clients[0].game!.finished,
        isTrue,
        reason: 'Match exceeded UI turn budget',
      );
      expect(clients[1].game!.finished, isTrue);
      expect(reconnected, isTrue);
      expect(
        clients[0].game!.state['placements'],
        clients[1].game!.state['placements'],
      );
      final clientResults = clients
          .map(
            (c) => {
              'match_id': c.profile!.match,
              'placements': c.game!.state['placements'],
              'ranking_awards': c.game!.state['ranking_awards'],
              'scores': {
                for (final p in (c.game!.state['players'] as Map).entries)
                  p.key: p.value['match_points'],
              },
            },
          )
          .toList();
      expect(
        clientResults[0],
        clientResults[1],
        reason: 'Both clients must show identical public final results',
      );
      expect((clients[0].game!.state['ranking_awards'] as Map).values.toSet(), {
        30,
        15,
      });
      debugPrint('UI results verified');
      await tester.runAsync(() async {
        final image =
            await (capture.currentContext!.findRenderObject()
                    as RenderRepaintBoundary)
                .toImage();
        final png = await image.toByteData(format: ui.ImageByteFormat.png);
        image.dispose();
        final out = Directory('../reports/two-client-ui');
        await out.create(recursive: true);
        await File('${out.path}/results.png')
            .writeAsBytes(png!.buffer.asUint8List());
        await File('${out.path}/report.json').writeAsString(
          jsonEncode({
            'match_id': clients[0].profile!.match,
            'placements': clients[0].game!.state['placements'],
            'ranking_awards': clients[0].game!.state['ranking_awards'],
            'reconnected': reconnected,
            'backend_restarted': restartSignal.isNotEmpty,
            'final_scores': {
              for (final c in clients)
                c.id: c.game!.player(c.id)['match_points'],
            },
            'client_results': clientResults,
            'identical_final_results': true,
            'turns': turns,
            'log': log,
          }),
        );
      });
      debugPrint('UI evidence saved');
      await tester.runAsync(() async {
        for (final c in clients) {
          c.dispose();
        }
        debugPrint('UI connections disposed');
        for (final c in clients) {
          await c.local.database.close().timeout(const Duration(seconds: 10));
        }
        debugPrint('UI databases closed');
      });
      debugPrint('UI cleanup resumed in test zone');
      await tester.pumpWidget(const SizedBox.shrink());
      debugPrint('UI widgets unmounted');
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      // The WebSocket adapter forwards sink.close in its subscription zone.
      // Even with dispose in runAsync, that zone can use the widget fake clock.
      // Advance the transport's five-second close-handshake deadline before
      // asserting teardown invariants; periodic application timers stay checked.
      await tester.pump(const Duration(seconds: 5));
      debugPrint('UI final frame pumped');
    },
    timeout: const Timeout(Duration(minutes: 20)),
  );
}
