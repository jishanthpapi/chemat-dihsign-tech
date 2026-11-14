# Deployment and development

Backend prerequisites: Python 3.11+, pip and optional Make; Docker/Compose for containers. Flutter stable with compatible Dart, Android SDK/JDK for Android; macOS and Xcode for iOS. There are no credentials or external services needed for the M1 tests.

Run `docker compose up --build` from repository root. Inspect `http://localhost:8000/health`; stop with `docker compose down`. The named volume reserves persistent storage for the later server SQLite implementation; current health service does not create or use a database. `CHEMAT_DATABASE_PATH` is a documented future configuration variable, not a claim of implemented persistence.

For a future hosted backend, build this Dockerfile on a host with a persistent local disk, mount `/app/storage`, back up SQLite consistently (SQLite backup API once implemented), and terminate TLS with a reverse proxy supporting WebSocket upgrades and suitable idle timeouts. Use one worker initially. Restrict inbound access, configure allowed origins and production credential/rate-limit controls when transport exists. Do not host real matches on the M1 health-only service. Never put secrets in the image or repository.

Android: generate the native project as described in README, configure Android SDK and application ID, run `flutter doctor`, `flutter test`, then `flutter build apk` for testing or `flutter build appbundle --release` for distribution. Configure release signing with external secrets before publishing. The current shell has no networking or profile storage.

iOS: on macOS generate the iOS host project, install Xcode command-line tools and required Flutter dependencies, run `flutter doctor`, `flutter test`, then `flutter build ios --no-codesign` for compilation validation. Configure bundle ID, signing team, provisioning and capabilities in Xcode before `flutter build ipa`. iOS signing and App Store distribution require Apple developer tooling and an appropriate developer account. Windows cannot validate an iOS build.

CI runs engine and health tests plus Flutter widget tests. Native builds and Docker deployment are separate future release gates. Resolve supported dependency versions into reviewed lock files before release; current version ranges are development bounds, not reproducible production locks.
