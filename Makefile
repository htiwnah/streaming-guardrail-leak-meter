PYTHON ?= python3

.PHONY: help lint test experiments receipts hygiene verify clean

help:
	@echo "Targets: lint, test, experiments, receipts, hygiene, verify, clean"

lint:
	$(PYTHON) tools/check_repo_hygiene.py --lint-only

test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v

experiments:
	$(PYTHON) experiments/run_experiments.py

receipts:
	$(PYTHON) tools/collect_metrics.py
	$(PYTHON) tools/check_numbers.py

hygiene:
	$(PYTHON) tools/check_repo_hygiene.py

verify: hygiene lint test receipts
	@echo "All verification checks passed."

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache build dist *.egg-info reports
