#!/usr/bin/env bash
set -euo pipefail

# Run the Appium URL E2E test suite.
# All config lives in FlintAPITest/AppiumURLTest/test.env
# See FlintAPITest/AppiumURLTest/test.env for required variables.
#
# Usage:
#   ./RunScripts/AppiumURLTest.sh                      # run all (env=preprod)
#   ./RunScripts/AppiumURLTest.sh -k TC-006            # run a specific test by ID
#   ./RunScripts/AppiumURLTest.sh -m security          # run one category
#   ./RunScripts/AppiumURLTest.sh --env staging        # include destructive tests
#   ./RunScripts/AppiumURLTest.sh --help               # pytest help

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../FlintAPITest/AppiumURLTest/run_tests.sh" "$@"
