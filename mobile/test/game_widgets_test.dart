// Presentation fixtures only; the live two-client test exercises real rules/server.
// ignore_for_file: deprecated_member_use
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:chemat/main.dart';
import 'package:chemat/app/controller.dart';
import 'package:chemat/core/api.dart';
import 'package:chemat/core/models.dart';
import 'package:chemat/core/storage.dart';

class EmptyVault implements CredentialVault {
  @override
  Future<String?> read() async => 'test';
  @override
  Future<void> write(String value) async {}
  @override
  Future<void> clear() async {}
}

Json state() => {
  'phase': 'reaction',
  'round': 2,
  'mini': false,
  'current': 'p1',
  'players': {
    'p1': {
      'task': 'Calcium carbonate',
      'pesos': 15,
      'match_points': 3,
      'savings': 2,
      'replacements': 0,
      'active': true,
      'forfeited': false,
    },
    'p2': {'pesos': 4, 'match_points': 1, 'active': true, 'forfeited': false},
  },
  'deadline': DateTime.now().millisecondsSinceEpoch / 1000 + 60,
  'recipe': {
    'name': 'Calcium carbonate',
    'reactants': ['Calcium chloride', 'Sodium carbonate'],
    'apparatus': ['Beaker', 'Stirring rod'],
    'difficulty': 'easy',
    'points': 1,
    'fee': 9,
  },
  'instances': {
    'card-1': ['reactant', 'Calcium chloride'],
    'card-2': ['reactant', 'Sodium carbonate'],
    'card-3': ['apparatus', 'Beaker'],
    'card-4': ['apparatus', 'Stirring rod'],
  },
  'task_id': 'task-1',
  'legal_commands': ['scan', 'end_reaction', 'offer', 'bank'],
  'choice': null,
  'incoming_attack': null,
  'pending_actions': [],
  'offers': {},
  'loans': {},
  'loan_history': [],
  'history': [],
  'placements': {'p1': null, 'p2': null},
  'forfeits': {},
  'ranking_awards': {},
};

void main() {
  sqfliteFfiInit();
  late AppController c;
  late LocalStore local;
  final sent = <Json>[];
  setUp(() async {
    sent.clear();
    local = await LocalStore.open(
      filename: inMemoryDatabasePath,
      factory: databaseFactoryFfi,
    );
    final api =
        GameApi(
            'http://test',
            client: MockClient((req) async {
              if (req.url.path.endsWith('/commands')) {
                sent.add(Map<String, dynamic>.from(jsonDecode(req.body)));
              }
              return http.Response(
                jsonEncode({'version': 2, 'state': state()}),
                200,
              );
            }),
          )
          ..playerId = 'p1'
          ..deviceCredential = 'test'
          ..accessToken = 'session';
    c = AppController(local: local, vault: EmptyVault(), api: api)
      ..profile = Profile(
        id: 'p1',
        username: 'Alice',
        endpoint: 'http://test',
        created: 'test',
        match: 'match-1',
      )
      ..initialized = true
      ..game = GameSnapshot({'version': 1, 'state': state()});
  });
  tearDown(() async {
    c.dispose();
    await local.database.close();
  });
  Future<void> mount(WidgetTester tester) async {
    tester.view.physicalSize = const Size(800, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    await tester.pumpWidget(ChematApp(controller: c));
  }

  Future<void> wait(WidgetTester tester) async {
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 150)),
    );
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets('dashboard task and server legal controls', (tester) async {
    await mount(tester);
    expect(find.textContaining('Task: Calcium carbonate'), findsOneWidget);
    expect(find.textContaining('Match Points: 3'), findsOneWidget);
    expect(
      tester
          .widget<OutlinedButton>(find.byKey(const ValueKey('buy-reactant')))
          .onPressed,
      isNull,
    );
    expect(
      tester
          .widget<FilledButton>(find.byKey(const ValueKey('end_reaction')))
          .onPressed,
      isNotNull,
    );
  });
  testWidgets(
    'scanner submits selected owned instance IDs and active Task ID',
    (tester) async {
      await mount(tester);
      await tester.tap(find.byKey(const ValueKey('scanner')));
      await tester.pumpAndSettle();
      for (var i = 1; i <= 4; i++) {
        await tester.tap(find.byKey(ValueKey('scan-card-$i')));
      }
      await tester.tap(find.byKey(const ValueKey('submit-scan')));
      await wait(tester);
      expect(sent.single['command'], 'scan');
      expect(sent.single['args']['task_id'], 'task-1');
      expect(sent.single['args']['card_ids'], [
        'card-1',
        'card-2',
        'card-3',
        'card-4',
      ]);
    },
  );
  testWidgets('optional defence choices come from server', (tester) async {
    final s = state()
      ..['phase'] = 'action_resolution'
      ..['choice'] = {
        'mode': 'redirect',
        'count': 1,
        'options': [null, 'p2'],
      }
      ..['legal_commands'] = ['choose'];
    c.game = GameSnapshot({'version': 1, 'state': s});
    await mount(tester);
    await tester.tap(find.widgetWithText(CheckboxListTile, 'Decline redirect'));
      await tester.pump();
    await tester.tap(find.text('Confirm response'));
    await wait(tester);
    expect(sent.single['command'], 'choose');
    expect(sent.single['args']['selected'], [null]);
  });
  testWidgets('results and connection loss are visible', (tester) async {
    c.game = GameSnapshot({
      'version': 1,
      'state': state()
        ..['phase'] = 'finished'
        ..['placements'] = {'p1': 1, 'p2': 2}
        ..['ranking_awards'] = {'p1': 30, 'p2': 15},
    });
    c.connection = 'Reconnecting (90-second grace)';
    await mount(tester);
    expect(find.text('Match complete'), findsOneWidget);
    expect(
      find.textContaining('You: place 1, Ranking Points 30'),
      findsOneWidget,
    );
    expect(find.text('Reconnecting (90-second grace)'), findsOneWidget);
  });
}
