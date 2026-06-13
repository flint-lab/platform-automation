# iOS Streaming Test

This document describes the purpose of the iOS streaming tests, prerequisites, and step-by-step instructions to run the tests locally.

## Overview

The iOS streaming test suite validates end-to-end streaming functionality on iOS devices. Tests are implemented in Python using `pytest` and live in the `FlintAPITest/IOSStreamingTest/` directory.

## Prerequisites

- Python 3.8+ installed
- Git (to clone/update the repository)

## Repository layout

- `FlintAPITest/IOSStreamingTest/` — test sources
  - test files (e.g. `test_ios_streaming.py`)
  - `conftest.py` — pytest fixtures and setup
  - `requirements.txt` — Python dependencies

## Setup

1. Create and activate a virtual environment (recommended):

```bash
# in the root folder of the repository
python3 -m venv venv
source venv/bin/activate
```

2. Install Python dependencies:

```bash
pip install --upgrade pip
pip install -r FlintAPITest/IOSStreamingTest/requirements.txt

```

3. Install Playwright browsers (required for the tests):

```bash
python -m playwright install

```

4. Google Chrome browser is required for the tests.

Please ensure it is installed and available in your system PATH.
```bash 
google-chrome --version

# If Chrome is not installed on Ubuntu:

apt update
apt install -y wget curl


wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt update
sudo apt install -y ./google-chrome-stable_current_amd64.deb
```

5. Ensure the test.env file is configured with the required environment variables.

```bash
# Set your environment variables here
TOKEN=<YOUR_PAT_TOKEN>
#change according to your environment
FLINT_API_BASE=https://staging.api.flintlab.io 

```


## Running the tests

Use the helper run script at `RunScripts/IOSStreamingTestRun.sh` from the repository root. It supports three modes:

- `html` (default): generate a timestamped HTML report
- `verbose`: run with `-v -s`
- `quiet`: run with `-q`

Examples:
# give execute permissions to the helper script
```bash
chmod +x RunScripts/IOSStreamingTestRun.sh
```

```bash
# default (html report)
./RunScripts/IOSStreamingTestRun.sh

# verbose
./RunScripts/IOSStreamingTestRun.sh verbose

# quiet
./RunScripts/IOSStreamingTestRun.sh quiet
```


# Note : 

- Automatic Device Allocation and Release: The tests will automatically acquire an available iOS device from the device pool, run the streaming tests, and release the device back to the pool after completion. This ensures efficient use of devices and allows multiple testers to run tests without conflicts.


- Report : HTML reports are generated in the root directory of the repository with the naming convention `IOSStreamingTestReport-YYYY-MM-DD--HH-MM-SS.html`. Each test run will create a new report with a unique timestamp.

- At least one iOS device must be available for the tests to run. If no devices are available, the tests will fail with an appropriate error message. Please ensure that at least one iOS device is available in the device pool before running the tests.

- these test runs only on chrome browser, please ensure that google chrome is installed and available in your system PATH.