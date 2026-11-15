import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/api.dart';
import '../core/models.dart';
import '../core/storage.dart';

class AppController extends ChangeNotifier {
  final LocalStore local;
  final CredentialVault vault;
  final GameApi api;
  Profile? profile;
  Json? lobby;
  GameSnapshot? game;
  Json catalog = {};
  List<dynamic> friends = [];
  List<dynamic> rankings = [];
  List<dynamic> foundPlayers = [];
  String? error;
  String? notice;
  String connection = 'Offline';
  bool busy = false;
  bool initialized = false;
  bool disposed = false;
  WebSocketChannel? channel;
  Timer? poll;
  Timer? retry;
  int backoff = 1;
  String? socketMatch;
  AppController({required this.local, required this.vault, required this.api});
  String get id => profile!.id;

  Future<void> initialize() async {
    await run(() async {
      final saved = await local.read('profile');
      if (saved != null) {
        profile = Profile.fromJson(saved);
        api.endpoint = profile!.endpoint;
        api.playerId = id;
        api.deviceCredential = await vault.read();
        if (api.deviceCredential == null) {
          throw ApiFailure(
            'Profile found but secure credential is missing. Account recovery is not available.',
            401,
          );
        }
        await api.renew();
        await refresh();
      }
      catalog = Map<String, dynamic>.from(
        await api.request('GET', '/catalog', private: false),
      );
      if (profile != null && profile!.match == null) {
        connection = 'Connected';
      }
    });
    initialized = true;
    poll = Timer.periodic(const Duration(seconds: 2), (_) {
      if (!busy) {
        refresh().catchError((Object e) {
          connection = 'Reconnecting';
          notify();
        });
      }
    });
    notify();
  }

  void notify() {
    if (!disposed) notifyListeners();
  }

  Future<void> run(Future<void> Function() operation) async {
    if (busy) return;
    busy = true;
    error = null;
    notify();
    try {
      await operation();
    } catch (e) {
      error = e is ApiFailure
          ? e.message
          : 'Connection or storage error. Retry when online.';
    }
    busy = false;
    notify();
  }

  Future<void> save() async {
    if (profile != null) await local.write('profile', profile!.toJson());
  }

  Future<void> register(String username, String endpoint) => run(() async {
    final uri = Uri.tryParse(endpoint.trim());
    if (uri == null ||
        !['http', 'https'].contains(uri.scheme) ||
        uri.host.isEmpty) {
      throw ApiFailure('Enter a valid backend URL', 400);
    }
    if (kReleaseMode && uri.scheme != 'https') {
      throw ApiFailure('Release builds require HTTPS', 400);
    }
    api.endpoint = endpoint.trim().replaceAll(RegExp(r'/$'), '');
    await api.register(username.trim());
    await vault.write(api.deviceCredential!);
    profile = Profile(
      id: api.playerId!,
      username: username.trim(),
      endpoint: api.endpoint,
      created: DateTime.now().toUtc().toIso8601String(),
    );
    await save();
    connection = 'Connected';
    catalog = Map<String, dynamic>.from(
      await api.request('GET', '/catalog', private: false),
    );
  });

  Future<void> availability(String username) => run(() async {
    final result = await api.request(
      'GET',
      '/usernames/${Uri.encodeComponent(username.trim())}',
      private: false,
    );
    notice = result['available'] == true
        ? 'Username available'
        : 'Username unavailable';
  });
  Future<void> rename(String username) => run(() async {
    await api.request('PATCH', '/players/me', body: {'username': username});
    profile = profile!.update(username: username.trim());
    await save();
  });
  Future<void> reset() => run(() async {
    await channel?.sink.close();
    channel = null;
    socketMatch = null;
    retry?.cancel();
    await vault.clear();
    await local.clear();
    profile = null;
    lobby = null;
    game = null;
    api.playerId = null;
    api.deviceCredential = null;
    api.accessToken = null;
  });
  Future<void> createLobby({bool public = false}) => run(() async {
    final result = await api.request(
      'POST',
      public ? '/matchmaking' : '/lobbies',
      body: {},
    );
    profile = profile!.update(lobby: result['code']);
    await save();
    await refresh();
  });
  Future<void> join(String code) => run(() async {
    code = code.trim().toUpperCase();
    await api.request('POST', '/lobbies/$code/join', body: {});
    profile = profile!.update(lobby: code);
    await save();
    await refresh();
  });
  Future<void> lobbyAction(String action) => run(() async {
    final route = '/lobbies/${profile!.lobby}/$action';
    final result = await api.request('POST', route, body: {});
    if (action == 'start') {
      profile = profile!.update(match: result['match_id']);
      await save();
    }
    if (action == 'leave' || action == 'cancel') {
      profile = profile!.update(clear: true);
      lobby = null;
      await save();
    }
    await refresh();
  });
  void apply(dynamic envelope) {
    if (envelope is! Map || envelope['state'] == null) return;
    final snapshot = GameSnapshot(Map<String, dynamic>.from(envelope));
    if (game == null || snapshot.version >= game!.version) {
      game = snapshot;
      notify();
    }
  }

  Future<void> refresh() async {
    if (profile == null) return;
    if (profile!.match != null) {
      apply(await api.request('GET', '/matches/${profile!.match}'));
      if (socketMatch != profile!.match && retry == null) {
        connect();
      }
    } else if (profile!.lobby != null) {
      lobby = Map<String, dynamic>.from(
        await api.request('GET', '/lobbies/${profile!.lobby}'),
      );
      if (['cancelled', 'expired'].contains(lobby!['status'])) {
        notice =
            'Lobby ${lobby!['status']}. You can create or join another lobby.';
        profile = profile!.update(clear: true);
        lobby = null;
        await save();
        notify();
        return;
      }
      if (lobby!['match_id'] != null) {
        profile = profile!.update(match: lobby!['match_id']);
        await save();
        await refresh();
      }
    }
    notify();
  }

  Future<void> connect() async {
    if (profile?.match == null || disposed) return;
    final match = profile!.match!;
    socketMatch = match;
    connection = 'Connecting';
    notify();
    try {
      final ws = await api.socket(match);
      channel = ws;
      connection = 'Connected';
      backoff = 1;
      notify();
      ws.stream.listen(
        (raw) {
          final data = jsonDecode(raw as String);
          if (data['error'] != null) {
            error = data['error'];
            notify();
            return;
          }
          apply(data['receipt'] ?? data);
        },
        onError: (Object e) {
          lost();
        },
        onDone: lost,
      );
      final pending = await local.read('pending');
      if (pending != null && pending['match'] == match) {
        try {
          apply(
            await api.request(
              'POST',
              '/matches/$match/commands',
              body: Map<String, dynamic>.from(pending['body']),
            ),
          );
        } catch (e) {
          error = 'Pending action could not be reconciled. State refreshed; review before repeating.';
        }
        await local.remove('pending');
        await refresh();
      }
    } catch (e) {
      lost();
    }
  }

  void lost() {
    if (disposed || profile?.match == null) return;
    socketMatch = null;
    connection = 'Reconnecting (90-second grace)';
    notify();
    retry?.cancel();
    retry = Timer(Duration(seconds: backoff), () {
      retry = null;
      connect();
    });
    backoff = min(8, backoff * 2);
  }

  Future<void> command(String command, [Json args = const {}]) => run(() async {
    if (game == null) return;
    final pending = await local.read('pending');
    if (pending != null) {
      try {
        apply(
          await api.request(
            'POST',
            '/matches/${pending['match']}/commands',
            body: Map<String, dynamic>.from(pending['body']),
          ),
        );
        notice = 'Previous action reconciled. Review the updated state before another action.';
      } on ApiFailure {
        await refresh();
        error = 'Previous action was not repeated. Review the current state.';
      }
      await local.remove('pending');
      return;
    }
    final request =
        '${DateTime.now().microsecondsSinceEpoch}-${Random.secure().nextInt(1 << 30)}';
    final body = {
      'request_id': request,
      'version': game!.version,
      'command': command,
      'args': args,
    };
    await local.write('pending', {'match': profile!.match, 'body': body});
    try {
      final result = await api.request(
        'POST',
        '/matches/${profile!.match}/commands',
        body: body,
      );
      apply(result);
      await local.remove('pending');
      if (result['expired'] == true) {
        error = 'Deadline passed. The server advanced play; your action was not applied.';
      }
    } on ApiFailure {
      await local.remove('pending');
      await refresh();
      rethrow;
    }
  });
  Future<void> leaveResults() => run(() async {
    await channel?.sink.close();
    profile = profile!.update(clear: true);
    socketMatch = null;
    game = null;
    lobby = null;
    await save();
  });
  Future<void> social({bool friendsOnly = false}) => run(() async {
    friends = await api.request('GET', '/friends');
    rankings = await api.request(
      'GET',
      friendsOnly ? '/leaderboard/friends' : '/leaderboard',
      private: friendsOnly,
    );
  });
  Future<void> search(String query) => run(() async {
    foundPlayers = await api.request(
      'GET',
      '/players/search?q=${Uri.encodeQueryComponent(query)}',
    );
  });
  Future<void> friendAction(String action, String other) => run(() async {
    if (action == 'remove') {
      await api.request('DELETE', '/friends/$other');
    } else {
      await api.request(
        'POST',
        '/friends/$action',
        body: {action == 'accept' ? 'sender' : 'target': other},
      );
    }
    friends = await api.request('GET', '/friends');
  });
  @override
  void dispose() {
    disposed = true;
    poll?.cancel();
    retry?.cancel();
    channel?.sink.close();
    api.close();
    super.dispose();
  }
}
