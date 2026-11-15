# CHEMa’t

Flutter/Dart client and FastAPI/Python authoritative server, retaining SQLite and standard Material widgets. Current verified status and remaining native release gates are in [IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md); reproduction and continuation instructions are in [PROJECT_HANDOFF.md](docs/PROJECT_HANDOFF.md). No custom artwork or interface redesign is included.

## Development

Python 3.11+: create/activate a virtual environment, then `python -m pip install -e ".[test]"`. Run `python -m pytest -q --junitxml=reports/backend-final.xml`. Start the backend with `python -m uvicorn chemat.api:app --app-dir backend --host 127.0.0.1 --port 8000`. API documentation: http://127.0.0.1:8000/docs.

Use Flutter 3.50.0 / Dart 3.14.0. From `mobile`, run `flutter pub get`, `flutter analyze`, `flutter test --concurrency=1 --machine`, then `flutter run --dart-define=BACKEND_URL=http://10.0.2.2:8000` for an Android emulator. Native Android/iOS host files are present. Release builds require HTTPS. A debug APK and real storage/authentication/restart recovery were verified on one Samsung Android 16 phone; see [native acceptance](docs/NATIVE_ACCEPTANCE.md) for evidence and remaining multi-device/release gates. In this Windows OneDrive checkout, run `./scripts/prepare_flutter_build.ps1` before switching build/test targets if generated caches retain read-only attributes.

## Two-client UI verification

From repository root, run `python scripts/run_two_client_ui.py`. The coordinator starts an isolated real backend and drives two independently authenticated Flutter client instances through ordinary UI controls. It interrupts a socket, restarts the server using the same SQLite database, completes a legitimate match, compares both public result sets and verifies persisted awards. It saves a readable screenshot, Flutter/server logs and JSON report under `reports/two-client-ui/`. Run Flutter test commands sequentially on Windows to avoid locking the native SQLite test DLL.

This harness uses the desktop Flutter test renderer, separate on-disk SQLite profiles and isolated test credential vaults. Separate real-plugin/storage and restart checks now passed on one Android phone; [native acceptance](docs/NATIVE_ACCEPTANCE.md) records that scope. Two-Android-device completion and iOS behavior remain unverified. See the handoff for exact evidence and limitations.

## Rules and deployment

The next native milestone and real platform storage probe are described in
[NATIVE_ACCEPTANCE.md](docs/NATIVE_ACCEPTANCE.md). Run
`python scripts/check_android.py` to record tooling/device readiness without
installing an SDK.

[Rulebook and amendment mapping](docs/RULEBOOK_MAPPING.md), [approved decisions](docs/OPEN_DECISIONS.md), [protocol](docs/PROTOCOL.md), [deployment](docs/DEPLOYMENT.md). The catalog and simplified recipes remain unchanged. Rebuild catalog exports/package data with `python scripts/build_catalog.py`. The server persists accepted authoritative commands and verifies all currency, ownership, phase and scoring changes. Never submit client-calculated results or expose credentials in logs.

`make setup`, `make test`, `make test-game`, `make test-multiplayer`, `make run-server`, `make run-mobile` remain available; Windows can run the equivalent commands in the Makefile. Source exports and original-file fingerprints are in `data/`.
