# Verified implementation status

## One-phone Android native checkpoint — 2026-11-15

The user approved the minimal toolchain after freeing disk space (35.57 GiB free
before installation). Temurin JDK 17.0.21+9 and Google SDK tools were installed in
`C:/Users/jisha/.chemat-tools/`; Flutter now uses those paths. API 36, Build Tools
36.0.0, platform-tools and NDK 28.2.13676358 were installed, with Platforms 34/35
and CMake 3.22.1 required by the existing plugins. No IDE or emulator installed.

**The APK and native tests actually ran on Samsung SM-M066B, Android 16/API 36.**
The corrected debug APK builds/installs/launches: `com.example.chemat`, 0.3.0+3,
min SDK 24, target/compile SDK 36, three ABIs. The real secure-storage/SQLite
probe passed. Normal UI registration, renewable authentication, forced process
termination/relaunch with the same permanent identity, and persisted SQLite
metadata with no credential/token fields were verified. A profile update after
backend restart returned PATCH 200 and survived another app relaunch.

Native recovery match `7e500238-2e1a-41d6-aa11-77b2d9636287` remained in reaction
round 1 with 3 cards, 1 peso, 0 savings and 0 Match Points across backend restart.
Native command receipts were preserved; the new server accepted authenticated
reads and a new WebSocket. An initial USB re-enumeration removed the test tunnel;
it was restored and a second backend-only restart passed without tunnel repair.
The peer was an authenticated host API client. **No two-Android-device full match
or native final scores/Ranking Points are claimed.** Only one phone was available.

Native QA fixed a misleading `Offline` home/lobby label after successful profile
restoration; the existing profile regression now asserts restored identity,
renewed token and `Connected` status. Match socket status remains unchanged.
Gradle memory/workers were bounded for the 8 GiB host. Read-only generated-cache
failures were resolved with `scripts/prepare_flutter_build.ps1`, which validates
and clears only ReadOnly attributes under generated `mobile/build`, skips links,
and deletes no files. Failed build/preparation attempts are retained separately.
All approved rules, architecture and standard Material interface are preserved.

Current automated results: backend **118 passed**; regular Flutter **6 passed,
2 opt-in live skips**; separate desktop live run **2 passed**; native storage
**1 passed**; analyzer **no issues**. Total **127 executed passes**, with the two
regular-suite live skips covered separately. Accepted regression/analyzer/native
test/final build commands exited 0;
intentionally terminated native backend processes exited 1 on Windows. Final
process audit found zero matching tests/compilers/backends. ADB remains installed
as tooling. [Machine-readable summary](evidence/android-native-2026-11-15/summary.json).
The separate desktop restart-recovery regression finished 10–5 with persisted
30/15 Ranking Points; those are desktop results, not the unfinished native match.

See [native acceptance](NATIVE_ACCEPTANCE.md) and
[evidence](evidence/android-native-2026-11-15/). APK SHA-256 is recorded there;
the final binary is `reports/android-native/chemat-debug.apk` (ignored artifact).
The local native backend/peer were stopped and USB test forwarding removed;
installation/profile remain on the phone. Native public HTTPS/WSS, two-device
completion, other Android versions, iOS and release signing remain unverified.
This section supersedes the preflight blockers below for the one-phone scope.

## Android native preflight — 2026-11-15 (not accepted)

Continued from clean `e2dac42`. Re-read native acceptance and handoff, then ran
doctor, device inventory, Java/disk checks and `flutter build apk --debug --no-pub`.
The build exited **1** with `No Android SDK found`; compilation never began and
no APK was produced. C: had about **1.8 GiB free**, the installed Java was **JRE 8**,
Android SDK/ADB were absent, and Flutter listed only Windows/Chrome/Edge devices.
Doctor also reported transient network probe failures to pub.dev/storage.googleapis.com;
recheck connectivity before downloads. Doctor exited 0 despite these failures.

The [minimum installation plan](NATIVE_ACCEPTANCE.md) preserves AGP 9.3.1,
Gradle 9.5.0, API 36, Build Tools 36.0.0 and NDK 28.2.13676358, with JDK 17.
Official repository metadata lists about **1.04 GB compressed SDK packages**;
extraction/JDK/Gradle/dependency/build space is additional. A **15 GiB free-space
planning allowance** is recommended, with no Android Studio/emulator included.
Installation approval and sufficient disk space are pending. No large dependency,
license acceptance, machine configuration, rule, architecture or UI change occurred.

Baseline backend regression reran: **118 passed, exit 0**. Flutter analysis:
**no issues, exit 0**. No configuration changes were made, so no
post-configuration Flutter/live/native regression result is claimed. The previous
126-pass milestone remains historical evidence, not a new native test result.
Android secure storage, relaunch persistence, authentication/networking, backend
restart recovery and a two-device match remain **unexecuted**. Native acceptance
is **not achieved**.

Evidence: [doctor](evidence/android-preflight-2026-11-15/doctor.log),
[devices](evidence/android-preflight-2026-11-15/devices.json),
[Java](evidence/android-preflight-2026-11-15/java.log),
[disk](evidence/android-preflight-2026-11-15/disk.json),
[APK attempt](evidence/android-preflight-2026-11-15/apk-build.log),
[package metadata](evidence/android-preflight-2026-11-15/sdk-package-sizes.json),
[backend JUnit](evidence/android-preflight-2026-11-15/backend.xml), and
[analysis](evidence/android-preflight-2026-11-15/flutter-analysis.log).

## Continuation verification — 2026-11-15

Started from clean local commit `b47781c`. Its accepted evidence is retained below;
the earlier 10–6 demonstration was followed by the recorded 14–5 acceptance run.
A fresh continuation run completed gameplay but reproduced an intermittent pending
WebSocket five-second close timer during Flutter teardown (exit 1, no hang).
The live harnesses now advance that transport deadline on the widget fake clock
before teardown invariants. No production component, rule or assertion was removed.

After the fix: **118 backend passes, 6 regular Flutter passes, 2 live passes**;
the two regular-suite live skips were executed separately. Flutter analysis passed.
The new live match finished **11–1** after 57 opportunities, both clients agreed,
and the coordinator verified persisted **30/15** awards exactly once after restart.
Flutter/coordinator exited 0; controlled servers were terminated/waited for
(Windows exits 1/1); the process audit found zero matching processes.
See [current report](evidence/continuation-2026-11-15/report.json),
[before-fix failure](evidence/continuation-2026-11-15/teardown-before.log),
[passing live log](evidence/continuation-2026-11-15/teardown-after.log),
[backend JUnit](evidence/continuation-2026-11-15/backend.xml),
[Flutter regression](evidence/continuation-2026-11-15/flutter-regression.jsonl),
[analysis](evidence/continuation-2026-11-15/flutter-analysis.log) and
[process audit](evidence/continuation-2026-11-15/process-audit.json).

Next milestone implementation adds a real-platform secure-storage/SQLite probe,
its locked Flutter integration-test dependency, a tooling/device readiness recorder,
and [native acceptance instructions](NATIVE_ACCEPTANCE.md). The probe is analyzed
but **not device-executed**. Fresh doctor/device inventory confirms no Android SDK
and no Android device. No SDK installation, APK, native launch or native acceptance
is claimed. The probe checks reopen in one process; relaunch and two-device network
acceptance remain required. Rules/amendments and architecture are unchanged.

During regression, OneDrive's read-only/reparse generated asset cache prevented
Flutter from preparing tests twice (before test execution). Verification succeeded
using a fresh ignored `.local/continuation-build` directory; the Flutter build-dir
setting was restored afterward. These preparation failures are excluded from the
126 executed passing tests; the reproduced live teardown failure is preserved above.

Verified on 2026-11-15. This verification milestone preserves FastAPI/Python, Flutter/Dart, SQLite and the existing standard Material interface. No major feature, Android SDK installation, artwork, external deployment or GitHub push was started during this pass.

## Final automated results

| Check | Actual result | Saved evidence |
|---|---|---|
| Full backend regression | 118 passed, 0 failed, 0 skipped; exit 0 | [JUnit](evidence/mobile-restart-2026-11-15/backend-final.xml), [log](evidence/mobile-restart-2026-11-15/backend-final.log) |
| Full regular Flutter regression | 6 passed, 0 failed; 2 opt-in live tests skipped; exit 0 | [JSON events](evidence/mobile-restart-2026-11-15/flutter-final.jsonl) |
| Real-backend live Flutter tests | 2 passed, 0 failed: full two-client UI match and cleanup probe; exit 0 | [Flutter log](evidence/mobile-restart-2026-11-15/flutter.log) |
| Flutter analyzer | No issues found; exit 0 | [Analyzer log](evidence/mobile-restart-2026-11-15/flutter-analysis.log) |
| Restart/recovery coordinator | Exit 0, persisted results and award ledger verified | [Coordinator log](evidence/mobile-restart-2026-11-15/two-client-coordinator.log), [exit](evidence/mobile-restart-2026-11-15/two-client-exit.json) |
| Post-run process audit | Zero matching test, compiler or backend processes | [Audit](evidence/mobile-restart-2026-11-15/process-audit.json) |

Total: **126 executed test passes, zero failures**. The two default-suite skips are the live tests executed separately by the coordinator; they are not additional passing tests. Earlier failed or hung attempts are excluded.

## Two-client restart-recovery acceptance

Match `3c353ac6-18c7-4d29-b167-9d3508c64d1c` completed after 81 UI turn opportunities. Two independently authenticated Flutter app/controller instances used separate SQLite profiles and separate HTTP/WebSocket connections. Registration, lobby readiness, purchases, gifts/trades, exact card scanner selection and turns used normal buttons/dialogs. The driver read authorized snapshots to choose moves; it did not inject resources, phases, scores or results.

The test interrupted a socket and restarted the real backend against the same database. Both clients recovered and finished with identical match ID, scores **14–5**, placements **first/second**, and Ranking Points **30/15**. The coordinator verified those awards in SQLite and exactly one persisted match result. See the [machine-readable report](evidence/mobile-restart-2026-11-15/report.json), [summary](evidence/mobile-restart-2026-11-15/summary.json), [server log](evidence/mobile-restart-2026-11-15/server.log), and [screenshot](evidence/mobile-restart-2026-11-15/results.png).

Flutter and the coordinator exited with code 0. Both controlled Uvicorn processes were intentionally terminated and waited for: once to simulate restart, once for final shutdown. Their Windows termination codes are 1, recorded explicitly in the report; they are not test failures. The process audit then found zero matching processes.

Harness fixes needed to establish completion: initialize network clients in the real async context, capture/dispose the screenshot image in that context, unmount widgets and pump the final frame, and explicitly close the coordinator's SQLite verification connection before temporary-directory cleanup. Earlier completed-match runs that stalled during teardown or failed coordinator cleanup are not accepted runs.

## Implemented source and rule authority

The existing engine covers the catalog/recipes, actions/defences/choices, regular/shared/mini-round scheduling, purchases, banking, proposals, loans, penalties, escrow, forfeits/defaults and placements. Server-authoritative accepted commands persist transactionally. Authenticated identities, renewable sessions, lobby readiness/presence, accepted friendships and UTC monthly Ranking Points remain on the same architecture. Flutter integrates profile/storage, HTTP/WS state recovery, gameplay controls, social/ranking screens and results using standard widgets.

Original rulebook rules and explicit user amendments remain distinguished in [OPEN_DECISIONS.md](OPEN_DECISIONS.md) and [RULEBOOK_MAPPING.md](RULEBOOK_MAPPING.md). The user-approved oldest-first server loan sequence resolves the previous insufficient-forfeit-assets arbitration blocker; voluntary repayment remains borrower-selected. Original inventory and recipes are unchanged.

## Remaining release blockers and limits

- This proves a desktop Flutter UI harness with two independent clients, not two physical devices. Test credential vaults do not establish Android Keystore or iOS Keychain behavior.
- Android SDK/device/emulator absent. The earlier debug-build attempt failed with `No Android SDK found`; no APK, Android launch or native secure-storage verification is claimed. Installation remains deferred.
- iOS needs macOS/Xcode; this host is Windows. Docker is unavailable, so container execution is unverified.
- Account recovery, multiple-device enrollment and broader ranked anti-collusion policy remain release work. Use one backend worker while socket subscriptions remain process-local; deployment requires HTTPS/WSS.

The user freed disk space themselves; the three previously proposed Flutter temporary compiler directories were not deleted. This document and its evidence are included in the local verification milestone commit. No remote push was performed. See [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) for reproduction.
