# Architecture

## Current structure
`data/` holds preserved workbook rows and a generated canonical catalog. `backend/chemat/engine.py` is a network-independent in-memory rule module. Seeded PRNG state is private. `api.py` exposes health only. `mobile/` holds a minimal Flutter status widget and test. No authoritative gameplay state is accepted from mobile.

## Target design
Flutter UI → authenticated HTTPS/WebSocket commands → FastAPI command validator → single-writer match scheduler → engine → SQLite transaction/outbox → per-viewer events. Separate transport, identity, persistence, and rules modules. Serialize commands per match; use one backend worker initially for SQLite and in-memory match ownership. Multi-worker scaling requires explicit coordination and is outside initial scope.

Mobile SQLite stores profile and cached statistics. OS secure storage holds a cryptographically generated device credential; SQLite never holds its plaintext. Device ID is a public identifier. Server enrolls a device once, hashes/verifies the credential, enforces authenticated ownership and rate limits, and never allows an ID-only overwrite. Reset warns of losing identity and recovery implications. Transport requires TLS outside local development.

Server SQLite stores minimal players, credential verifiers, friendships, lobbies, match snapshots/events, verified results and monthly ranking ledger. Transactions atomically persist results and unique ranking awards keyed by match/player/season; restart/replay cannot double-award. Version catalog, state and protocol. Persist PRNG state or event outcomes for restart determinism; never disclose seeds/deck order to clients.

Every command carries match ID, request ID and expected version. Authenticate membership, validate turn/phase/targets/resources, apply atomically, persist, then emit redacted snapshots. Duplicate requests return recorded outcomes. Reconnect supplies last event sequence and receives authorized replay or snapshot. Secret tasks, hands, credentials and future cards must never leak through broadcasts, logs or errors. M1 `snapshot` filters other hands/tasks; transport and adversarial privacy tests remain future work.

Reaction contexts must be created only by the trusted scheduler. A client submits compound intent, never a phase context, hand, score, die result or recipe. Current isolated opportunities intentionally lack full phase orchestration and must not be wired directly to public endpoints.
