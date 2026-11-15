# Project handoff — verified restart-recovery milestone

## Latest: one-phone Android verification (2026-11-15)

User-approved installation completed after disk cleanup. Flutter uses JDK
`C:/Users/jisha/.chemat-tools/jdk-17.0.21+9` and SDK
`C:/Users/jisha/.chemat-tools/android-sdk`; global Java/PATH were not replaced.
Read the latest IMPLEMENTATION_STATUS.md and NATIVE_ACCEPTANCE.md sections first.

A debug APK and real storage probe ran on Samsung SM-M066B (Android 16/API 36).
Registration/authentication, SQLite/secure credential persistence across forced
app termination, and same-match backend restart recovery passed on the phone.
Post-restart profile rename returned 200 and persisted across relaunch. The
recovery match remains unfinished; its peer was a host API test client, not a
second Android device. Two-Android-device complete-match acceptance is next.
No gameplay rule or artwork changes were made.

Final automation: **127 passes** (118 backend, 6 regular Flutter, 2 desktop live,
1 native storage), analyzer clean, zero lingering matching processes. The two
regular-suite live skips ran separately. The desktop regression finished 10–5
with 30/15 persisted Ranking Points. That completed desktop match is separate
from the unfinished native recovery match. See the current evidence summary.

Native QA fixed the restored-profile `Offline` status label and extended the
existing profile regression. Gradle now uses a 2 GiB heap/two workers. Before
switching Flutter test/build targets in this checkout, use
`./scripts/prepare_flutter_build.ps1` if generated files retain ReadOnly flags.
It touches only generated cache attributes and deletes nothing. The corrected
APK is `reports/android-native/chemat-debug.apk`; its hash, native logs and
screenshots are tracked under `evidence/android-native-2026-11-15/`.

The test backend/peer and USB forwarding were stopped after verification. The
phone's test profile/app remain installed. To resume this isolated match, start
the backend against `reports/android-native/server.sqlite3` on host port 8766,
then use `adb reverse tcp:8000 tcp:8766`. App endpoint is `http://127.0.0.1:8000`.
USB re-enumeration removes forwarding; restore it after reconnecting the cable.
No SDK/emulator download or native runtime gate should be inferred complete for
another machine/device. No push or external deployment was performed.

Earlier checkpoints below are retained as historical evidence.

## Android preflight checkpoint (2026-11-15)

Native acceptance was attempted from `e2dac42` but is **not achieved**. The debug
APK command failed before compilation because Android SDK is missing. Only about
1.8 GiB free on C:, Java 8 runtime rather than JDK 17, and no Android device.
No dependencies were installed and no Flutter/Android configuration was changed.
Installation approval and disk space are pending; do not infer approval from the
installation commands in [NATIVE_ACCEPTANCE.md](NATIVE_ACCEPTANCE.md). That document
now contains the minimum components, official sources, disk estimate, setup
commands and physical-phone networking route. Evidence and current test results
are in the Android preflight section of IMPLEMENTATION_STATUS.md. Once approved
and installed, build and execute the actual Android gates, then run regressions.

## Latest continuation checkpoint (2026-11-15)

Read the continuation section of [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
first. Starting from `b47781c`, a new live run reproduced an intermittent pending
WebSocket close-handshake timer at teardown. Both live tests now advance its
five-second deadline on the widget fake clock. The subsequent full coordinator run
passed both live tests, exited 0, verified identical **11–1** results and **30/15**
persisted awards after restart, and left zero matching processes. Backend: 118
passes; regular Flutter: 6 passes/2 opt-in live skips; analyzer: no issues.
Before/after logs and current evidence are in `evidence/continuation-2026-11-15/`.
The prior accepted 14–5 evidence below is preserved as historical evidence.

The next unfinished milestone remains native Android acceptance. Implemented its
real-plugin storage probe in `mobile/integration_test/native_storage_test.dart`
and `python scripts/check_android.py` readiness capture. Follow
[NATIVE_ACCEPTANCE.md](NATIVE_ACCEPTANCE.md). Doctor confirms missing SDK and no
Android devices; the new native test is analyzed but unexecuted. SDK installation
remains deferred, and app relaunch/two-device networking are separate checks.
Do not treat desktop or in-process storage tests as full native acceptance.

## Scope and completed checklist

Preserved FastAPI/Python, Flutter/Dart, SQLite and the current standard-widget interface. No new major feature, artwork, Android SDK installation, external deployment or GitHub push was performed during verification.

- [x] Rerun the complete two-client restart-recovery test.
- [x] Verify identical final match IDs, scores, placements and Ranking Points on both clients.
- [x] Confirm Flutter/coordinator exit 0 and zero lingering test/backend processes.
- [x] Run the full backend suite: 118 passed, 0 failed, 0 skipped.
- [x] Run the full regular Flutter suite: 6 passed, 0 failed, 2 opt-in live skips; run those 2 live tests separately: both passed.
- [x] Run Flutter analysis: no issues found.
- [x] Save screenshot, server/Flutter/coordinator logs, JUnit/JSON reports and process audit.
- [x] Update IMPLEMENTATION_STATUS.md with final results and limitations.
- [x] Include the verified milestone in a local commit; retrieve its hash with `git log -1 --format=%H`. No push.

## Final evidence

[Evidence summary](evidence/mobile-restart-2026-11-15/summary.json) records **126 executed passes, zero failures**, coordinator exit 0 and zero matching processes after shutdown. The two default-suite live skips are covered by the separate live invocation.

Both clients finished with scores **14–5**, identical placements and **30/15** Ranking Points. The real backend was restarted against its existing database; clients recovered, finished using UI controls, and the coordinator checked the stored result and awards exactly once. [Report](evidence/mobile-restart-2026-11-15/report.json), [screenshot](evidence/mobile-restart-2026-11-15/results.png), [logs](evidence/mobile-restart-2026-11-15/flutter.log), [process audit](evidence/mobile-restart-2026-11-15/process-audit.json).

The two Uvicorn processes were intentionally terminated for restart/final shutdown and waited for; Windows codes 1 are expected and recorded. Flutter and coordinator both exited 0. Earlier teardown hangs and a coordinator SQLite cleanup failure were fixed in the harness and excluded from accepted evidence.

## Reproduce

From the repository root, with Python dependencies installed:

```text
python -m pytest -q --junitxml=reports/backend-final.xml
python scripts/run_two_client_ui.py
```

From mobile, with Flutter 3.50.0/Dart 3.14.0 available:

```text
flutter analyze
flutter test --concurrency=1 --machine
```

The coordinator locates Flutter on PATH or in `.tools/flutter`, starts a fresh isolated FastAPI server/database, runs both live tests, restarts the backend without changing its database, verifies the persisted awards, closes its verification connection, and stops/waits for its subprocesses. Working artifacts go to `reports/two-client-ui/`; the accepted snapshot is tracked in `docs/evidence/mobile-restart-2026-11-15/`. Do not run separate Flutter test commands concurrently on Windows because the native SQLite DLL can remain loaded during a test.

## What the demonstration establishes

Two separately authenticated Flutter app/controller instances have separate on-disk SQLite profiles, test credential vaults and HTTP/WebSocket connections. The full-match driver uses ordinary app controls and authorized client snapshots; no gameplay state/resources/scores are injected. Socket interruption and backend restart are harness fault injection. The cleanup probe uses direct API setup only to test teardown and is not counted as another UI match.

This is a desktop Flutter UI integration harness, not two physical Android devices. Test vaults do not verify Android Keystore/iOS Keychain. Native acceptance remains a separate release gate.

## Remaining blockers

- Android SDK/device/emulator absent; earlier APK build stopped with `No Android SDK found`. No APK or native launch is verified. SDK installation remains deferred.
- iOS requires macOS/Xcode; current host is Windows. Docker execution is unverified because the runtime is unavailable.
- Account recovery, multiple-device enrollment and ranked anti-collusion policy remain release work. Server socket subscriptions require one worker; deployment needs HTTPS/WSS.
- No remaining rule arbitration blocker: insufficient forfeit assets settle oldest server loan first, per user approval. Original rules versus approved amendments are documented in OPEN_DECISIONS.md and RULEBOOK_MAPPING.md.
- The user chose to free disk space themselves; the three previously proposed temporary compiler folders were not removed.

## Source locations

- `mobile/test/two_client_live_test.dart`: real-backend UI match and screenshot/report generation.
- `mobile/test/cleanup_live_probe_test.dart`: asynchronous resource cleanup diagnostic.
- `scripts/run_two_client_ui.py`: server restart coordinator and persisted-award verification.
- `mobile/lib/app/controller.dart`, `views.dart`: existing app integration and standard widgets.
- `docs/IMPLEMENTATION_STATUS.md`: current verified status; this document supersedes earlier in-progress milestone notes.

The next release step is native Android build/device and secure-storage verification when the user resumes that scope. No installation or new major feature was begun as part of this milestone.
