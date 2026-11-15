.PHONY: setup test test-game test-multiplayer run-server run-mobile
setup:
	python -m pip install -e ".[test]"
test:
	python -m pytest -q --junitxml=reports/pytest.xml
test-game:
	python -m pytest -q backend/tests/test_engine.py backend/tests/test_amendments.py backend/tests/test_simulation.py --junitxml=reports/game.xml
test-multiplayer:
	python -m pytest -q backend/tests/test_multiplayer.py --junitxml=reports/multiplayer.xml
run-server:
	python -m uvicorn chemat.api:app --app-dir backend --host 127.0.0.1 --port 8000
run-mobile:
	cd mobile && flutter run
