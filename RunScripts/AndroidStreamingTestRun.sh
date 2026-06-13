#!/usr/bin/env bash
set -euo pipefail

# Usage: AndroidStreamingTestRun.sh [mode]
# Modes:
#   quiet    - quiet run (`-q`) [default]
#   verbose  - verbose with -v -s
#   html     - generate HTML report (`--html=report.html --self-contained-html`)

MODE=${1:-html}
case "$MODE" in
	quiet)
		pytest -q AndroidStreamingTest/test_android_streaming.py
		;;
	verbose)
		pytest -v -s AndroidStreamingTest/test_android_streaming.py
		;;
	html)
		pytest -v AndroidStreamingTest/test_android_streaming.py --html=AndroidStreamingTest-$(date +%Y-%m-%d)--$(date +%H-%M-%S).html --self-contained-html
		;;
	*)
		echo "Unknown mode: $MODE — falling back to html"
		pytest -v AndroidStreamingTest/test_android_streaming.py --html=AndroidStreamingTest-$(date +%Y-%m-%d)--$(date +%H-%M-%S).html --self-contained-html
		;;
esac
