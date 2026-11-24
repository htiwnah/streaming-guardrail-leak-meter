#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"

python3 "${ROOT_DIR}/tools/check_repo_hygiene.py"
python3 -m unittest discover -s "${ROOT_DIR}/tests" -p "test_*.py" -v
python3 "${ROOT_DIR}/tools/collect_metrics.py"
python3 "${ROOT_DIR}/tools/check_numbers.py"
