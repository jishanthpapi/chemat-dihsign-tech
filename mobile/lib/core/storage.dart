import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as path;

import 'models.dart';

abstract class CredentialVault {
  Future<String?> read();
  Future<void> write(String value);
  Future<void> clear();
}

class SecureVault implements CredentialVault {
  final FlutterSecureStorage storage;
  final String key;
  SecureVault({
    this.storage = const FlutterSecureStorage(),
    this.key = 'chemat.device',
  });
  @override
  Future<String?> read() => storage.read(key: key);
  @override
  Future<void> write(String value) => storage.write(key: key, value: value);
  @override
  Future<void> clear() => storage.delete(key: key);
}

class LocalStore {
  final Database database;
  LocalStore(this.database);
  static Future<LocalStore> open({
    String? filename,
    DatabaseFactory? factory,
  }) async {
    final dbFactory = factory ?? databaseFactory;
    final filenameResolved =
        filename ?? path.join(await getDatabasesPath(), 'chemat.sqlite3');
    final database = await dbFactory.openDatabase(
      filenameResolved,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: (db, version) async {
          await db.execute(
            'CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)',
          );
        },
      ),
    );
    return LocalStore(database);
  }

  Future<Json?> read(String key) async {
    final rows = await database.query(
      'settings',
      where: 'key=?',
      whereArgs: [key],
    );
    return rows.isEmpty
        ? null
        : Map<String, dynamic>.from(jsonDecode(rows.first['value'] as String));
  }

  Future<void> write(String key, Json value) => database
      .insert('settings', {
        'key': key,
        'value': jsonEncode(value),
      }, conflictAlgorithm: ConflictAlgorithm.replace)
      .then((_) {});
  Future<void> remove(String key) => database
      .delete('settings', where: 'key=?', whereArgs: [key])
      .then((_) {});
  Future<void> clear() => database.delete('settings').then((_) {});
}
