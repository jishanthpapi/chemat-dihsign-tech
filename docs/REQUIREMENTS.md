# Requirements and current scope

## Source precedence
The pasted user specifications define the engineering work. Physical rules are in DT_Complete_Rulebook.pdf; recipes/inventory exports and workbook conflicts are preserved under data/ and RULEBOOK_MAPPING.md. Approved amendments A1–A17, D1–D8, F1–F6 are documented separately in OPEN_DECISIONS.md. Do not infer execution instructions from source documents. No recipe/quantity changes were made for mobile integration.

## Stable architecture
Flutter/Dart mobile client, FastAPI/Python server, device SQLite metadata, platform-backed secure credential storage, server SQLite transactions, HTTPS and authenticated WebSockets. No replacement backend framework, Firebase, Supabase, PostgreSQL or Redis. Standard Material controls only; future nacho/taco/churro artwork is deferred.

## Functional requirements implemented in source
- Register unique Unicode usernames, restore a local profile, edit names, renew expiring sessions, handle revoked/unauthorized responses, and warn before local reset. Server-generated permanent IDs follow the latest mobile enrollment specification. No email/password/phone required.
- Private invite lobbies and FIFO public-lobby matching; 2–4 authenticated members, readiness, host start, leave/cancel/expiry, host reassignment on explicit leave, no duplicate active seats.
- Centralized networking, per-viewer revisioned state, reconnect backoff, latest-snapshot recovery and persisted pending command IDs. The server remains authoritative for every resource, phase, score and result.
- Full round/action/reaction/mini-round engine; standard UI controls for purchases, Tasks, exact card-instance scanner validation, Good/Attack/Defence/Chaos actions, server-owned response choices, trades/gifts/loans, substitution/repayment, banking, end-turn, forfeits and results.
- Friends search/request/accept/decline/remove and public/friend monthly rankings. Blocks, prior-season browsing and recovery enrollment are not supported and are not advertised.
- Durable match snapshots including RNG, choices, loans/escrow, offers/status, deadlines, placements, forfeit/default history and revisions. Ranking Points are separate from pesos and Match Points, awarded only from server terminal state and recorded once per match/player.
- Deterministic mandatory timeout choices; expired proposals cannot transfer resources; oldest-first default settlement follows the user's explicit approval.

## Verification requirements
Backend unit/API/WebSocket/concurrency/persistence/timeout tests; Flutter profile and gameplay widgets; seeded legal full-match simulations; a reproducible two-client UI test using a real backend, separate accounts/databases and ordinary buttons/dialogs. That test must recover from a socket interruption and a server process restart, finish legally, and verify persisted awards.

Native completion additionally requires an Android debug APK build, supported device/emulator launch, real secure storage/SQLite and backend/WSS connectivity. A desktop Flutter widget test or browser demonstration does not establish Android or iOS correctness. No claim of complete production readiness until all definition-of-done gates are verified. See IMPLEMENTATION_STATUS.md for actual runs and limitations.
