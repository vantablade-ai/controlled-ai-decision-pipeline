.PHONY: install test check demo run
install:
	python -m pip install -r requirements-dev.txt
test:
	pytest -q
check:
	ruff check .
	python -m compileall -q app tests scripts
	pytest -q
demo:
	python scripts/demo.py
run:
	uvicorn app.main:app --reload
