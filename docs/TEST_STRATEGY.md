# Test strategy

## Executed milestone 1
Run `python -m pytest -q --junitxml=reports/pytest.xml`. Tests cover 211-card counts and type/category subtotals, recipe references/fees, all 20 compound recipes and base rewards, 2–4-player deterministic setup, secret task/hand filtering, purchase fees/timing/exhaustion, separate reshuffle, and atomic rejection for wrong phase/player/task, missing cards/money and repeated opportunities. Health API is exercised using FastAPI TestClient. Actual run: **42 passed**. This is not full-match or WebSocket coverage.

Run `python scripts/build_catalog.py` to regenerate catalog from preserved rows. Future source extraction dependencies are optional. JUnit XML is generated under ignored `reports/`; CI uploads it even on failure.

## Planned verification
- Unit fixtures for every action, defensive priority, Chaos immunity, multiplier expiry, task replacement, round and mini-round boundaries, banking/trade cutoffs, frozen scores and placement.
- Resource conservation across deck/hand/discard/task/queued-action zones; peso transfers including bank; failed commands have no state changes.
- Deterministic full-match agent simulation with recorded seed, command log, rule/catalog version, terminal result and explicit turn budget. Timeout is a test failure, not a fabricated winner.
- API integration against temporary SQLite: credentials/ownership, lobby capacity, invite codes, matchmaking, consent and results.
- WebSocket tests for concurrent/double/out-of-turn commands, idempotency, version conflicts, disconnect/reconnect, redaction and process restart recovery.
- Ranking tests for durable once-only awards, month boundaries and approved formula.
- Flutter widget/profile tests and device integration tests for local restoration, reset warning, secure storage, connection loss and scanner responses.
- End-to-end two-device/emulator flow from account creation to match result; headless protocol simulation covers rules independently of UI.

Flutter/Dart are unavailable in the current environment. Widget tests are provided but were not executed. Docker builds, Android/iOS builds and full deployment were not executed. At M1 only the health endpoint was available; the amendment milestone below replaces that limited multiplayer test target.

## Amended milestone execution (2026-11-14)
The earlier execution notes describe M1 only. The expanded suite now has **105 passing tests**, actually executed with `python -m pytest -q --junitxml=reports/pytest.xml`. `test-multiplayer` now runs the real API, WebSocket, SQLite, identity, friend, concurrency, timer and ranking tests in test_multiplayer.py. `test-game` runs engine, amendment and legal simulation tests. AMENDMENT_STATUS.md indexes each amendment's explicit regressions.

The six simulation scenarios (seeds 7/19 × 2/3/4 players) are each run twice to verify deterministic placements. They use legal engine commands without injecting resources, assert conservation at each step, and fail on budget exhaustion. API near-terminal and debt/action fixtures are separately labeled. Flutter, Docker and native builds remain unexecuted; no decorative UI changes were made.

Additional executed checks: built chemat-0.2.0 wheel using an isolated pip build; scripts/verify_package.py loaded the bundled catalog and set up 211 cards outside the source checkout. scripts/smoke_server.py started a real uvicorn process, enrolled two authenticated players, created/joined/started a lobby, accepted a turn command and verified SQLite creation. The initial non-isolated packaging attempt failed because the host lacked bdist_wheel; the isolated build resolved that environment issue.
