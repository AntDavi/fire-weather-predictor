#!/bin/bash
# CI local — espelha o GitHub Actions workflow.
# Rode a partir da raiz do repositório: bash scripts/ci.sh
set -e

BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)/backend"
cd "$BACKEND_DIR"

echo "==> [1/3] Ruff (linter)..."
ruff check .

echo ""
echo "==> [2/3] Bandit (security scan)..."
bandit -r app/ -ll

echo ""
echo "==> [3/3] Pytest (tests + coverage)..."
pytest tests/ --cov=app --cov-report=term-missing

echo ""
echo "CI PASSED!"
