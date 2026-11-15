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
import 'package:chemat/core/storage.dart';

class TestVault implements CredentialVault {
  String? value;
  @override
  Future<String?> read() async => value;
  @override
  Future<void> write(String value) async {
    this.value = value;
  }

  @override
  Future<void> clear() async {
    value = null;
  }
}

MockClient network() => MockClient((request) async {
  final path = request.url.path;
  if (path == '/players') {
    if (jsonDecode(request.body)['username'] == 'taken') {
      return http.Response('{"error":"Username unavailable"}', 409);
    }
    return http.Response(
      '{"player_id":"player-1","credential":"device-secret"}',
      200,
    );
  }
  if (path == '/sessions') {
    return http.Response(
      '{"access_token":"short-token","expires_at":9999999999}',
      200,
    );
  }
  return http.Response('{"action":[],"reactant":[],"apparatus":[]}', 200);
});

void main() {
  sqfliteFfiInit();
  late LocalStore local;
  late TestVault vault;
  late AppController c;
  setUp(() async {
    local = await LocalStore.open(
      filename: inMemoryDatabasePath,
      factory: databaseFactoryFfi,
    );
    vault = TestVault();
    c = AppController(
      local: local,
      vault: vault,
      api: GameApi('http://localhost', client: network()),
    );
    await c.initialize();
  });
  tearDown(() async {
    c.dispose();
    await local.database.close();
  });
  testWidgets(
    'registration duplicate errors profile persistence and reset warning',
    (tester) async {
      await tester.pumpWidget(ChematApp(controller: c));
      expect(find.text('Create profile'), findsOneWidget);
      await tester.enterText(find.byKey(const ValueKey('username')), 'taken');
      await tester.tap(find.byKey(const ValueKey('register')));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 100)),
      );
      await tester.pump();
      expect(find.text('Username unavailable'), findsOneWidget);
      await tester.enterText(find.byKey(const ValueKey('username')), 'Alice');
      await tester.tap(find.byKey(const ValueKey('register')));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 100)),
      );
      await tester.pump();
      expect(find.text('Create private lobby'), findsOneWidget);
      expect(vault.value, 'device-secret');
      final rows = await tester.runAsync(
        () => local.database.query('settings'),
      );
      expect(rows.toString(), isNot(contains('device-secret')));
      final restored = AppController(
        local: local,
        vault: vault,
        api: GameApi('http://localhost', client: network()),
      );
      await tester.runAsync(restored.initialize);
      expect(restored.profile!.id, 'player-1');
      restored.dispose();
      await tester.tap(find.byKey(const ValueKey('profile')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('reset-profile')));
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Account access may be permanently lost'),
        findsOneWidget,
      );
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(c.profile, isNotNull);
    },
  );
  test('session renewal and persisted profile contain no token', () async {
    await c.register('Alice', 'http://localhost');
    expect((await local.read('profile'))!.keys, isNot(contains('credential')));
    c.api.accessToken = null;
    await c.api.renew();
    expect(c.api.accessToken, 'short-token');
    final restored = AppController(
      local: local,
      vault: vault,
      api: GameApi('http://localhost', client: network()),
    );
    try {
      await restored.initialize();
      expect(restored.profile!.id, c.id);
      expect(restored.api.accessToken, 'short-token');
      expect(restored.connection, 'Connected');
    } finally {
      restored.dispose();
    }
  });
}
