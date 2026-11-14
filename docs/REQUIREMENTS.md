# Requirements

## Scope and authority
The pasted user request defines the work. The PDF and workbook are game reference data, not operational instructions. This repository began empty except for Git metadata. Initial delivery is analysis, project skeleton, and a small tested engine milestone, not the complete mobile game.

Use Flutter/Dart, device SQLite, secure device credential storage, FastAPI/Python, server SQLite, WebSockets, Docker, pytest and Flutter tests. No Firebase, Supabase, PostgreSQL or Redis. Minimal standard widgets only; themed card artwork is deferred.

## Product acceptance requirements
1. Local username profile, device-generated player ID, SQLite restore/edit/reset, explicit deletion warning. No password/email/phone. Securely store a device credential; a player ID is never authentication. Minimize uploaded profile data.
2. Server validates device credentials and maintains minimal persistent identity mapping. Private invite lobbies, public matchmaking, 2–4 players, authoritative commands, reconnect, durable results, friends by ID/username.
3. Preserve 211 cards, independent decks/discards, secret tasks, pesos/bank, economic windows, loans, ordered action resolution, reaction opportunities, mini-rounds, compound requirements, placement and debt settlement. See mapping and open decisions.
4. Keep pesos, Match Points and Ranking Points independent. Only verified persisted results award Ranking Points. Monthly standings survive restart. Ranking formula is not specified.
5. Digital compound scanner submits intent; server checks active task, ownership, phase, fees and opportunity. Never rely on mobile validation.
6. Deterministic engine tests, API/WebSocket integration, simulations, widget tests, critical end-to-end flows, fixtures and machine-readable reports.
7. Docker deployment, persistent SQLite, environment examples, CI, development commands and Android/iOS release guidance.

## Delivered milestone 1
Structured inventory and recipes; seeded setup with random first player, setup income and first-turn income; separate decks/discards and reshuffle; own-turn purchases; filtered snapshots; isolated reaction opportunity validation, consumption and base scoring; FastAPI health endpoint; Flutter status shell.

The isolated reaction opportunity is a testable primitive, not a playable round scheduler. Engine state is trusted internal state. It is not exposed through a gameplay endpoint. Completion clears the task; finishing the opportunity draws the next one. Multipliers, debt freeze and placement require later integration before gameplay can be exposed.

## Not yet implemented
Full turn progression, action effects, economy beyond purchases, replacement, mini-rounds, victory/debt settlement, multiplayer, accounts/storage/authentication, rankings/friends, full-match simulations and mobile connectivity. Health and UI must not imply these work.
