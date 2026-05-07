#!/bin/bash
# Placeholder — implementar na Issue #1.3
set -e

echo "==> Ruff (linter)..."
ruff check .

echo "==> Bandit (security scan)..."
bandit -r app/ -ll

echo "==> Pytest (tests + coverage)..."
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=70

echo ""
echo "CI PASSED!"
