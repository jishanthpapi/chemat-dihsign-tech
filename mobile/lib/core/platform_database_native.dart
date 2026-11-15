import 'storage.dart';

Future<LocalStore> openPlatformDatabase() => LocalStore.open();
