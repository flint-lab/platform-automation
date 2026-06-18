#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load test.env using python-dotenv so quoted values and spaces are handled correctly
if [ -f test.env ]; then
  eval "$(python -c "
from dotenv import dotenv_values
import shlex, sys
for k, v in dotenv_values('test.env').items():
    print(f'export {k}={shlex.quote(v or \"\")}')
" 2>/dev/null)" || { echo "ERROR: Failed to load test.env — is python-dotenv installed? Run: pip install -r requirements.txt"; exit 1; }
fi

ALLURE_RESULTS="allure-results"
ALLURE_REPORT="allure-report"
HTML_REPORT="report.html"

echo "============================================"
echo " FlintAPI — Appium URL E2E Tests"
echo " Target: ${FLINT_BASE_URL:-NOT SET}"
echo " Note  : destructive tests run only with --env staging"
echo "============================================"
echo ""

# Install dependencies if needed
if ! python -m pytest --version > /dev/null 2>&1; then
  echo "Installing dependencies..."
  pip install -r requirements.txt
fi

# Run tests — disable exit-on-error here so report generation always runs
set +e
pytest . \
  -v \
  -s \
  --tb=long \
  --alluredir="$ALLURE_RESULTS" \
  --html="$HTML_REPORT" \
  --self-contained-html \
  "$@"
TEST_EXIT_CODE=$?
set -e

echo ""
echo "============================================"
echo " Generating Allure Report"
echo "============================================"

if command -v allure > /dev/null 2>&1; then
  allure generate "$ALLURE_RESULTS" -o "$ALLURE_REPORT" --clean
  echo ""
  echo " Reports generated:"
  echo "   HTML (quick view) : $SCRIPT_DIR/$HTML_REPORT"
  echo "   Allure (full)     : $SCRIPT_DIR/$ALLURE_REPORT/index.html"
  echo ""
  echo " To open Allure report: allure open $ALLURE_REPORT"
else
  echo " Allure CLI not found. Only HTML report generated."
  echo " Install: https://allurereport.org/docs/install/"
  echo ""
  echo " Report: $SCRIPT_DIR/$HTML_REPORT"
fi

echo "============================================"
exit $TEST_EXIT_CODE
