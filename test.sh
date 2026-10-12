#!/usr/bin/env bash
# this_file: test.sh
set -euo pipefail
cd "$(dirname "$0")"
uv run --extra test python -m pytest -xq --cov=vexy_subs --cov-fail-under=80
uv run --extra test ruff check src tests
