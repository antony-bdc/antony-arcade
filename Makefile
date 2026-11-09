.PHONY: lint test build serve

lint:
	ruff check .
	ruff format --check .

test:
	python3 -m pytest -q

build:
	python3 -m showcase.build games site

serve: build
	python3 -m http.server -d site 8000
