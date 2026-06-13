#!/usr/bin/env bash
set -euo pipefail

# Usage: IOSStreamingTestRun.sh [mode]
# Modes: html (default), verbose, quiet

MODE=${1:-html}
case "$MODE" in
  quiet)
    pytest -q FlintAPITest/IOSStreamingTest
    ;;
  verbose)
    pytest -v -s FlintAPITest/IOSStreamingTest
    ;;
  html)
    pytest -v FlintAPITest/IOSStreamingTest --html=IOSStreamingTestReport-$(date +%Y-%m-%d)--$(date +%H-%M-%S).html --self-contained-html
    ;;
  *)
    echo "Unknown mode: $MODE — falling back to html"
    pytest -v FlintAPITest/IOSStreamingTest --html=IOSStreamingTestReport-$(date +%Y-%m-%d)--$(date +%H-%M-%S).html --self-contained-html
    ;;
esac
