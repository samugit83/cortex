PY ?= python3

.PHONY: test lint golden verify

test:
	$(PY) -m unittest discover -s tests -t . -q

lint:
	$(PY) tools/lint.py

golden:
	$(PY) tools/golden.py

verify: test lint
