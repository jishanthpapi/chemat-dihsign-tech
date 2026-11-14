.PHONY: setup test test-game test-multiplayer run-server run-mobile
setup:
	python -m pip install -e ".[test]"
test:
	python -m pytest -q --junitxml=reports/pytest.xml
test-game:
	python -m pytest -q -k "not health" --junitxml=reports/game.xml
test-multiplayer:
	python -m pytest -q -k health --junitxml=reports/health.xml
run-server:
	python -m uvicorn chemat.api:app --app-dir backend --host 127.0.0.1 --port 8000
run-mobile:
	cd mobile && flutter run
