import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as path;

import 'package:chemat/core/storage.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('native credential and SQLite persistence across reopen', (
    tester,
  ) async {
    // Use isolated names so this probe never changes an enrolled profile.
    final suffix = DateTime.now().microsecondsSinceEpoch;
    final key = 'chemat.native-probe.$suffix';
    final filename = path.join(
      await getDatabasesPath(),
      'chemat-native-probe-$suffix.sqlite3',
    );
    final vault = SecureVault(key: key);
    LocalStore? local;
    try {
      expect(await vault.read(), isNull);
      await vault.write('probe-credential-$suffix');
      local = await LocalStore.open(filename: filename);
      await local.write('profile', {'player': 'probe-player'});
      await local.database.close();
      local = null;

      // New wrappers must read from the actual platform plugins, not a fake.
      final reopenedVault = SecureVault(
        storage: const FlutterSecureStorage(),
        key: key,
      );
      expect(await reopenedVault.read(), 'probe-credential-$suffix');
      local = await LocalStore.open(filename: filename);
      expect(await local.read('profile'), {'player': 'probe-player'});
      final rows = await local.database.query('settings');
      expect(rows.toString(), isNot(contains('probe-credential-$suffix')));

      await reopenedVault.clear();
      expect(await vault.read(), isNull);
      await local.remove('profile');
      expect(await local.read('profile'), isNull);
    } finally {
      await local?.database.close();
      await vault.clear();
      await deleteDatabase(filename);
    }
  });
}
