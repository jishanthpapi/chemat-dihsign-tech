# Implementation plan

Each milestone leaves a runnable health service and tests. Do not expose a partial rule engine as ranked gameplay.

| Milestone | Work | Exit criteria |
|---|---|---|
| M1 / phase 1–2, delivered | source analysis, structured catalog, decks, setup, purchases, isolated compound primitive | inventory, all recipes, atomic rejection, privacy and seed tests |
| M2 / phase 2 | full scheduler, task replacement, queues, all action effects, multipliers, mini-rounds | fixture coverage of §§4,10–18; resolve relevant open rules first |
| M3 / phase 2 | banking, trade/gift consent, loans, settlement, placement | conservation, windows, deadlines, score freeze, full seeded match simulation |
| M4 / phase 3 | SQLite identities/device credentials, private/public lobbies, authenticated WebSockets, reconnect/results | API and socket integration, replay, restart persistence, privacy |
| M5 / phase 4 | Flutter native scaffolds, SQLite profiles, secure storage, username edit/reset warning/connectivity | widget and device lifecycle tests |
| M6 / phase 5 | minimal gameplay controls and digital scanner | two clients complete verified match, reconnect scenario |
| M7 / phase 6 | friends, monthly ranking ledger | approved ranking formula; duplicate/restart/season-boundary tests |
| M8 / phase 7–8 | broaden automation, packaging, deployment and release readiness | full-match simulation, E2E, Android build, macOS iOS build, deployment smoke test |

Resolve open rules in small batches before dependent implementation. Test fixtures that inject resources are unit fixtures, not simulations or evidence of a completed playable match.
