import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

import 'models.dart';

class ApiFailure implements Exception {
  final String message;
  final int status;
  ApiFailure(this.message, this.status);
  @override
  String toString() => message;
}

class GameApi {
  final http.Client client;
  String endpoint;
  String? playerId;
  String? deviceCredential;
  String? accessToken;
  GameApi(this.endpoint, {http.Client? client})
    : client = client ?? http.Client();
  Future<dynamic> request(
    String method,
    String route, {
    Json? body,
    bool private = true,
    bool retry = true,
  }) async {
    if (private && accessToken == null) {
      await renew();
    }
    final uri = Uri.parse('$endpoint$route');
    final response = await client
        .send(
          http.Request(method, uri)
            ..headers.addAll({
              'Content-Type': 'application/json',
              if (private) 'X-Player-ID': playerId!,
              if (private) 'X-Device-Credential': accessToken!,
            })
            ..body = body == null ? '' : jsonEncode(body),
        )
        .timeout(const Duration(seconds: 15));
    final text = await response.stream.bytesToString();
    dynamic result = text.isEmpty ? {} : jsonDecode(text);
    if (response.statusCode == 401 && private && retry) {
      await renew();
      return request(method, route, body: body, retry: false);
    }
    if (response.statusCode >= 400) {
      throw ApiFailure(
        (result['error'] ?? result['detail'] ?? 'Request failed').toString(),
        response.statusCode,
      );
    }
    return result;
  }

  Future<void> renew() async {
    if (playerId == null || deviceCredential == null) {
      throw ApiFailure(
        'Local credentials missing. Reset or restore this device.',
        401,
      );
    }
    final session = await request(
      'POST',
      '/sessions',
      private: false,
      body: {'player_id': playerId, 'credential': deviceCredential},
    );
    accessToken = session['access_token'];
  }

  Future<void> register(String username) async {
    final result = await request(
      'POST',
      '/players',
      private: false,
      body: {'username': username},
    );
    playerId = result['player_id'];
    deviceCredential = result['credential'];
    await renew();
  }

  Future<WebSocketChannel> socket(String match) async {
    await renew();
    final uri = Uri.parse('$endpoint/matches/$match/ws')
        .replace(scheme: endpoint.startsWith('https') ? 'wss' : 'ws');
    final channel = WebSocketChannel.connect(uri);
    await channel.ready;
    channel.sink.add(
      jsonEncode({'player_id': playerId, 'credential': accessToken}),
    );
    return channel;
  }

  void close() => client.close();
}
