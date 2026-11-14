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

Flutter/Dart are unavailable in the current environment. Widget tests are provided but were not executed. Docker builds, Android/iOS builds and full deployment were not executed. `test-multiplayer` currently checks health only and must not be described as multiplayer validation.
