.PHONY: setup lint test run example clean

setup:
	python -m pip install -U pip
	python -m pip install -e .[dev]

lint:
	python -m ruff check src tests
	python -m ruff format --check src tests

test:
	python -m pytest -q

run:
	python -m indestructibleautoops run --config configs/indestructibleautoops.pipeline.yaml --project .

example:
	bash examples/run.sh

clean:
	rm -rf .indestructibleautoops .pytest_cache .ruff_cache dist build *.egg-info