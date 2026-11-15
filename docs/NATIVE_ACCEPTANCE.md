# Native Android acceptance

Android acceptance covers debug builds, device launch, platform storage and
device networking. The verified scope below is one physical phone. The existing
Flutter/FastAPI/SQLite architecture and all approved rules remain unchanged.

## Verified one-phone checkpoint — 2026-11-15

The debug APK and the following checks **actually ran on a Samsung SM-M066B**,
Android 16/API 36, arm64-v8a. This is no longer only desktop evidence.

| Gate | Observed result |
|---|---|
| Debug APK build/install/launch | Passed; `com.example.chemat`, version 0.3.0+3, min SDK 24, target/compile SDK 36; debug signed, three ABIs |
| Real platform storage probe | 1 native integration test passed; secure credential write/read/delete and SQLite close/reopen/cleanup |
| Registration/authentication | Normal app fields/buttons; server enrollment/session/catalog returned 200 over the USB-forwarded development backend |
| Process termination/relaunch | Same permanent player ID recovered; sessions renewed using the persisted secure credential; on-device SQLite contained metadata, no credential/token fields |
| Backend restart recovery | Same match `7e500238-2e1a-41d6-aa11-77b2d9636287` recovered automatically with forwarding intact; new server accepted WebSocket/authenticated reads |
| State integrity | Reaction round 1, 3 cards, 1 peso, 0 savings, 0 Match Points preserved; four accepted native command receipts retained |
| Post-restart write/relaunch | Profile rename via UI returned PATCH 200; updated name and same match survived another force-stop/relaunch |
| Full two-Android-device match | **Not run**: only one Android phone available; the second participant was an authenticated host API test peer |

Evidence and APK SHA-256 are in `evidence/android-native-2026-11-15/`. The final
normal APK is `reports/android-native/chemat-debug.apk` (ignored build artifact,
not committed). The native match was a recovery smoke test, not a completed
ranked match; no native finishing scores or Ranking Points are claimed. No game
state, resource or score injection was used. The host peer only joined/readied
and issued a legal end-turn; phone actions used normal app controls.

The first restart attempt was interrupted by USB re-enumeration, which removed
ADB forwarding. The app correctly remained reconnecting. After restoring the
tunnel it recovered; a second backend-only restart passed without tunnel repair.
This verifies debug HTTP/WebSocket networking through `adb reverse`, not native
public HTTPS/WSS deployment. One device/OS was tested; no hardware-key attestation,
iOS run, release signing or two-device acceptance is claimed.

Native QA exposed an incorrect `Offline` home/lobby label after successful cold
profile restoration. `AppController.initialize` now sets `Connected` after
successful authenticated initialization when there is no match; match socket
status remains owned by the existing WebSocket flow. The existing profile test
now asserts restored identity/session/status. No rule or interface redesign.

Switching between native-test and normal APK builds exposed read-only generated
entries in this OneDrive checkout (`unit_test_assets`, native asset JNI libraries,
and merged native libraries). Failed preparation/build logs are preserved and
excluded from passing results. From repository root, before switching targets:

```powershell
./scripts/prepare_flutter_build.ps1
```

This helper validates the generated `mobile/build` path, skips symbolic links and
junctions, and clears only ReadOnly attributes. It does not delete files or modify
source or other caches. The successful corrected APK build followed this step.
The local test backend/peer were stopped and test USB forwarding removed after
verification; app installation/profile remain. Recreate the backend and forwarding
before trying to resume this isolated development match.

## Readiness (no installation)

From the repository root run `python scripts/check_android.py`. It records
`flutter doctor -v` and machine-readable device inventory in
`reports/android-readiness/`. A successful tool invocation does **not** mean
Android acceptance passed: doctor can exit zero with a missing toolchain.
Review its Android section and select an Android device from the inventory.
This script neither installs tools nor accepts licenses.

## Approved toolchain installation (2026-11-15)

The user approved the minimal installation after freeing disk space; C: then had
35.57 GiB free. Installed outside OneDrive:

- JDK: `C:/Users/jisha/.chemat-tools/jdk-17.0.21+9` (Eclipse Temurin; official
  GitHub release archive verified against its published SHA-256).
- SDK: `C:/Users/jisha/.chemat-tools/android-sdk` (official Google packages).
- Flutter `android-sdk` and `jdk-dir` configuration now point to those paths.
  This does not replace the user's system Java 8 or globally change PATH.
- API 36, Build Tools 36.0.0, platform-tools and NDK 28.2.13676358 installed.
  The first Gradle build additionally required Platforms 34 and 35 for the pinned
  plugins; these compile SDK dependencies do not lower the app's target API 36.
  JNI/native plugin configuration also installed CMake 3.22.1.
- No Android Studio, emulator or system image installed. One Samsung SM-M066B
  phone (Android 16/API 36, arm64-v8a) is connected for runtime checks.
- The 8 GiB host uses a 2 GiB Gradle heap, 1 GiB metaspace limit, two workers and
  512 MiB Kotlin daemon heap instead of the generated 8 GiB/4 GiB defaults.

The latest `sdkmanager.bat` compatibility wrapper returned exit 0 even while
splitting semicolon package names and installing only platform-tools. The tested
replacement uses the Android CLI with slash-separated names:

```powershell
& '<sdk>/cmdline-tools/latest/bin/android.exe' '--sdk=<sdk>' sdk install platforms/android-36 build-tools/36.0.0 ndk/28.2.13676358
```

Verify the actual `source.properties` files and doctor results after installation;
exit 0 alone is insufficient. The command-line tools archive was checked against
the SHA-1 supplied by Google's repository XML; that metadata references a newer
archive than the download page's displayed SHA-256 table. Preserve the recorded
checksum algorithm rather than claiming a published SHA-256 comparison for it.

## Original minimum installation plan (preflight record)

Preflight from `e2dac42` on 2026-11-15 found only about 1.8 GiB free on C:, no
Android SDK/ADB or Android device, and Java runtime 8 rather than a JDK. The APK
command exited 1 before compilation: `No Android SDK found`. Evidence is in
`evidence/android-preflight-2026-11-15/`. No installation or Flutter configuration
change was made. Native acceptance remains unverified.

The current project uses AGP 9.3.1 and Gradle 9.5.0. Its installed Flutter
3.50.0 specifies compile/target API 36 and NDK 28.2.13676358. Preserve these
versions for the first build. The smallest practical setup for a physical phone
does not require Android Studio, an emulator, or a system image:

| Component | Required version/purpose |
|---|---|
| JDK | 17, including `javac`; the installed Java 8 runtime is insufficient |
| Android command-line tools | Bootstrap SDK package installation |
| `platform-tools` | ADB and physical-device communication |
| `platforms;android-36` | Project compile SDK |
| `build-tools;36.0.0` | AGP 9.3 default/minimum build tools |
| `ndk;28.2.13676358` | Existing Flutter/project pin; do not silently remove it |
| Gradle/Maven artifacts | Wrapper downloads Gradle 9.5.0 and resolved build dependencies |

Official sources: [AGP compatibility](https://developer.android.com/build/releases/agp-9-3-0-release-notes),
[Flutter Android setup](https://docs.flutter.dev/platform-integration/android/setup),
[SDK package manager](https://developer.android.com/tools/sdkmanager), and
[command-line tools download](https://developer.android.com/studio#command-tools).
The package manager documentation now marks `sdkmanager` deprecated in favor of
`android sdk`; its documented compatibility commands below remain available.

Google's stable Windows package metadata totals 1,035,698,716 compressed bytes
for these five SDK packages (about 1.04 GB decimal); it excludes the JDK,
extraction, Gradle/Maven caches and build output. This is a metadata estimate,
not downloaded packages or an installed-size measurement. Reserve at least
15 GiB free as a planning allowance and recheck before installation. Exact
requirements can grow; an emulator adds substantial storage and is excluded.
Keep SDK/JDK outside OneDrive, and account for user/Gradle/temp caches on C:
even if SDK files go to another volume. No existing files are approved for deletion.

After explicit installation approval and sufficient free space:

1. Install a trusted JDK 17 distribution, verify `java -version` and
   `javac -version`, and record the chosen installation path.
2. Download the official Windows command-line tools archive, verify its
   published SHA-256, and extract as `<sdk>/cmdline-tools/latest/bin/...`.
3. Set the current shell's `JAVA_HOME` to that JDK and add its `bin` to PATH.
   Review/accept the SDK licenses using `sdkmanager.bat --sdk_root=<sdk> --licenses`.
4. Install only the listed SDK packages with the command below. Do not add
   emulator/system-image/CMake packages unless a demonstrated need is approved.
5. Configure Flutter with the actual installed paths, rerun doctor/device
   inventory, and then build. Do not configure nonexistent placeholder paths.

PowerShell command templates (replace all placeholders before executing):

```powershell
& '<sdk>/cmdline-tools/latest/bin/sdkmanager.bat' '--sdk_root=<sdk>' 'platform-tools' 'platforms;android-36' 'build-tools;36.0.0' 'ndk;28.2.13676358'
& '<flutter>/bin/flutter.bat' config '--android-sdk=<sdk>' '--jdk-dir=<jdk17>'
& '<flutter>/bin/flutter.bat' doctor -v
& '<sdk>/platform-tools/adb.exe' devices -l
```

Enable USB debugging and authorize the host on a connected Android phone;
install the manufacturer's USB driver only if needed. A USB-connected phone can
use `adb reverse tcp:8000 tcp:8000` and app backend `http://127.0.0.1:8000`,
avoiding LAN routing changes. Keep the same backend database across its restart.
Run the regression suites sequentially after configuration, then execute the
native probe and manual relaunch/network checks below. Save device model/API,
APK hash, command exits and redacted logs; two-device match acceptance requires
two independently authenticated Android clients. A one-device run cannot satisfy it.

## Platform storage probe

From `mobile`, after an Android SDK and device are available:

```text
flutter pub get
flutter build apk --debug
flutter test integration_test/native_storage_test.dart -d <android-device-id>
```

The integration test uses real `flutter_secure_storage` and `sqflite` plugins.
It verifies credential read/write/delete, metadata persistence after database
close/reopen, and absence of the probe credential from SQLite settings. Unique
test-only key/database names and finally cleanup protect an enrolled profile.
It does not use the desktop harness's in-memory credential vault.

This proves plugin persistence across wrapper/database reopen in one process.
It does not prove app termination/relaunch persistence or hardware-backed key
properties. Also verify manually on the device: register against a reachable
development backend, terminate and relaunch the app, recover the same identity,
and reconnect to the same match. Retain device/OS, command exits and logs without
credentials. Test two-device completion/restart recovery separately. Emulator
backend URL is `http://10.0.2.2:8000`; a physical device needs a reachable host
address. Debug allows HTTP; release requires HTTPS/WSS.

Release signing, application ID selection and distribution remain separate
gates. The current example application ID and debug signing are not production
configuration. No release build or native acceptance is claimed until executed
on the appropriate platform.
