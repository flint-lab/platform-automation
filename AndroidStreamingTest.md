# Android Streaming Test

This document describes the Android streaming tests, prerequisites, and step-by-step instructions to run the tests locally.

## Overview

The Android streaming test suite validates end-to-end streaming functionality on Android devices. Tests are implemented in Python using `pytest` and live in the `AndroidStreamingTest/` directory.

## Prerequisites

- Python 3.8+ installed, virtual environment recommended
- Git (to clone/update the repository)

## Repository layout

- `FlintAPITest/AndroidStreamingTest/` — test sources
	- `test_android_streaming.py` — main test file
	- `conftest.py` — pytest fixtures and setup
	- `requirements.txt` — Python dependencies
	- `test.env` — environment variables used by the tests (secrets/config)

## Setup

1. Create and activate a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install Python dependencies:

```bash
pip install --upgrade pip
pip install -r FlintAPITest/AndroidStreamingTest/requirements.txt
```

3. Ensure the `test.env` file is properly configured with necessary environment - Environment Variables in `FlintAPITest/AndroidStreamingTest/test.env`
```bash
TOKEN=<YOUR_PAT_TOKEN>
FLINT_API_BASE=https://staging.api.flintlab.io // change according to your environment
HEARTBEAT_WAIT=5 // wait time in seconds for the heartbeat to be sent
```

## Running the tests

- From the repository root (recommended):

```bash
pytest -q FlintAPITest/AndroidStreamingTest/test_android_streaming.py
```


(Or)

## Android Streaming Tests using the helper script

Run the Android streaming tests located in the `AndroidStreamingTest/` directory. A helper script is provided at `RunScripts/AndroidStreamingTestRun.sh` to run the suite in several modes.

Quick start (from the repository root):

```bash
# create and activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install --upgrade pip
pip install -r FlintAPITest/AndroidStreamingTest/requirements.txt

# permit execution of the helper script
chmod +x RunScripts/AndroidStreamingTestRun.sh

# run the helper script (defaults to HTML report)
./RunScripts/AndroidStreamingTestRun.sh

# or run verbose
./RunScripts/AndroidStreamingTestRun.sh verbose

# or run quiet
./RunScripts/AndroidStreamingTestRun.sh quiet
```
