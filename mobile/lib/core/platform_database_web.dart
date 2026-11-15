import 'package:sqflite_common_ffi_web/sqflite_ffi_web.dart';

import 'storage.dart';

Future<LocalStore> openPlatformDatabase() =>
    LocalStore.open(filename: 'chemat.sqlite3', factory: databaseFactoryFfiWeb);
