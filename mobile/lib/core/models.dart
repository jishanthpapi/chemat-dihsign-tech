typedef Json = Map<String, dynamic>;

class Profile {
  final String id;
  final String username;
  final String endpoint;
  final String created;
  final String? lobby;
  final String? match;
  Profile({
    required this.id,
    required this.username,
    required this.endpoint,
    required this.created,
    this.lobby,
    this.match,
  });
  Json toJson() => {
    'id': id,
    'username': username,
    'endpoint': endpoint,
    'created': created,
    'lobby': lobby,
    'match_id': match,
  };
  factory Profile.fromJson(Json j) => Profile(
    id: j['id'],
    username: j['username'],
    endpoint: j['endpoint'],
    created: j['created'],
    lobby: j['lobby'],
    match: j['match_id'],
  );
  Profile update({
    String? username,
    String? lobby,
    String? match,
    bool clear = false,
  }) => Profile(
    id: id,
    username: username ?? this.username,
    endpoint: endpoint,
    created: created,
    lobby: clear ? null : lobby ?? this.lobby,
    match: clear ? null : match ?? this.match,
  );
}

class GameSnapshot {
  final int version;
  final Json state;
  GameSnapshot(Json envelope)
    : version = envelope['version'],
      state = Map<String, dynamic>.from(envelope['state']);
  String get phase => state['phase'];
  String? get current => state['current'];
  List<String> get legal => List<String>.from(state['legal_commands'] ?? []);
  Json player(String id) => Map<String, dynamic>.from(state['players'][id]);
  Json get instances => Map<String, dynamic>.from(state['instances'] ?? {});
  Json? get recipe => state['recipe'] == null
      ? null
      : Map<String, dynamic>.from(state['recipe']);
  Json? get choice => state['choice'] == null
      ? null
      : Map<String, dynamic>.from(state['choice']);
  bool get finished => phase == 'finished';
}
