#!/usr/bin/env bash
set -euo pipefail

# Run the Emulator Device E2E test suite.
# All config lives in FlintAPITest/EmulatorDeviceTest/.env
# See FlintAPITest/EmulatorDeviceTest/.env.example for required variables.
#
# Usage:
#   ./RunScripts/EmulatorDeviceTest.sh              # run all tests
#   ./RunScripts/EmulatorDeviceTest.sh -k TC-024    # run a specific test by ID
#   ./RunScripts/EmulatorDeviceTest.sh --help       # pytest help

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../FlintAPITest/EmulatorDeviceTest/run_tests.sh" "$@"
