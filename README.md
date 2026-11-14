# CHEMa’t

Initial engine milestone, not yet a playable multiplayer app. Start with [requirements](docs/REQUIREMENTS.md), [mapping](docs/RULEBOOK_MAPPING.md) and [open decisions](docs/OPEN_DECISIONS.md).

Python 3.11+: `python -m venv .venv`, activate it, then `python -m pip install -e ".[test]"`. Run `python scripts/build_catalog.py`, `python -m pytest -q --junitxml=reports/pytest.xml`, and `python -m uvicorn chemat.api:app --app-dir backend --host 127.0.0.1 --port 8000`. Health: `http://127.0.0.1:8000/health`.

Make equivalents: `make setup`, `make test`, `make test-game`, `make test-multiplayer`, `make run-server`, `make run-mobile`. On Windows without Make, use the Python commands above; `test-game` selects tests except health and `test-multiplayer` selects health only. No simulated full match exists yet.

Flutter stable with Dart >=3.5 is required for mobile. From `mobile`, run `flutter create --platforms=android,ios --project-name chemat .` to generate native host projects, then `flutter pub get`, `flutter test`, and `flutter run`. This repository contains the Dart shell; platform scaffolds are not generated or verified here. No custom styling is included.

See [deployment guide](docs/DEPLOYMENT.md) for Docker and mobile builds. Bundled source exports can be used without the original Downloads files. Source fingerprints are in `data/source-manifest.json`; rebuild canonical data with `scripts/build_catalog.py`. The original documents remain untouched.
