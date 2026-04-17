#!/usr/bin/env bash
# Build the HTML dashboard from repo root (safe to run from any cwd).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f pyproject.toml ]]; then
  echo "error: pyproject.toml not found in $ROOT" >&2
  exit 1
fi
PY="${PY:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "error: need $PY on PATH (install Python 3.11+)" >&2
  exit 1
fi
"$PY" -m venv .venv
./.venv/bin/python -m pip install -q -U pip
./.venv/bin/python -m pip install -q -e .
./.venv/bin/ren-econ seed --db data/wind_demo.sqlite
./.venv/bin/ren-econ build-index --db data/wind_demo.sqlite --out-dir dist
echo "Built: $ROOT/dist/index.html (+ per-project dashboards)"
if command -v open >/dev/null 2>&1; then
  open "$ROOT/dist/index.html" || echo "hint: open dist/index.html in your browser" >&2
fi
