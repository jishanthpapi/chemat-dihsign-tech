# Architecture

## Implemented
`engine.py` retains card/setup primitives. `match.py` owns amended round progression, actions and player selections, mini-rounds, economics, debt, escrow and placements. Internal state and PRNG are JSON-serializable with schema version 2. `catalog.json` is bundled package data; data/catalog.json remains the reviewable generated export.

`store.py` uses SQLite transactions (BEGIN IMMEDIATE) to serialize writers, check match versions, persist every accepted command and idempotency receipt, and atomically record terminal results and one award per match/player. Rejected commands roll back both state and RNG. Duplicate request IDs with identical intent return the latest authorized snapshot without reapplying the command; conflicting reuse is rejected. UTC calendar-month award partitions implement monthly reset while preserving history.

`api.py` authenticates HTTP headers and first WebSocket messages. ID alone never authenticates. Registration returns a random device credential once; only its SHA-256 digest is stored. Credentials have cryptographic entropy, unlike human passwords. Username uniqueness uses a trimmed Unicode casefold key. Server-generated IDs currently back the protocol; device-generated local profile IDs and enrollment migration remain mobile work.

HTTP and WebSocket commands use the same store. Authenticated membership is checked before snapshots and commands. Broadcasts are rendered separately for each viewer. Other hands/tasks, future deck order, RNG state and private selection options are excluded. Server-side clocks apply before commands and in a one-second background tick loop. Disconnect time, missed-turn counts, timer configuration and pending selections survive restart. A timely reconnect grants a fresh regular-turn timer if it is that player's turn.

The service reloads authoritative state per operation and serves current snapshots on reconnect; event-history replay/outbox is not implemented. Use one uvicorn worker: socket subscriptions and broadcasts are process-local. SQLite transactions coordinate commands but do not provide multi-process socket fan-out.

## Remaining release work
Flutter local SQLite profiles and OS-secure credential storage, automatic client reconnect, gameplay controls, production rate limiting, credential recovery/rotation, ranked anti-collusion controls and native-device E2E tests. The status shell is intentionally unchanged.

TLS is required for deployments. Credentials must never appear in URLs or application logs. No client-supplied state, placement, score, seed or result is authoritative. Mandatory card selections remain blocked pending a player response if their negotiation timer expires; no automatic card-choice rule has been approved. Forfeit placement/debt handling remains explicit unresolved state, so those matches cannot award Ranking Points.

## Current mobile implementation and verification note
The earlier remaining-work paragraphs describe the previous engine milestone. The client now implements SQLite metadata, secure-storage integration, standard-widget gameplay, HTTP/WS synchronization, pending-command reconciliation and reconnect. Sessions expire after 15 minutes and can be renewed with a verified device credential; revocation invalidates both. Username uniqueness normalizes NFC/casefold. Lobby schema v4 includes readiness, lifecycle and a 90-second host-presence lease. Final approved mandatory-choice timeouts and oldest-first forfeit settlement are implemented. These additions retain the same Flutter/FastAPI/SQLite architecture. See IMPLEMENTATION_STATUS.md and PROJECT_HANDOFF.md for current test evidence and native-platform limits; those documents supersede outdated milestone status prose above.
