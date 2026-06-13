# Emulator Device Test

This document describes the emulator device E2E tests, prerequisites, and step-by-step instructions to run the tests locally.

## Overview

The emulator device test suite validates end-to-end emulator management functionality via FlintAPI. Tests cover allocation, APK install, file upload, screen recording, and log download. Tests are implemented in Python using `pytest` and live in the `FlintAPITest/EmulatorDeviceTest/` directory.

## Prerequisites

- Python 3.10+ installed, virtual environment recommended
- Git (to clone/update the repository)
- A valid FlintAPI Personal Access Token

## Repository layout

- `FlintAPITest/EmulatorDeviceTest/` — test sources
  - `test_allocation.py` — emulator allocation tests (TC-001, TC-002)
  - `test_stop.py` — emulator stop tests (TC-021)
  - `test_apk_install.py` — APK install tests (TC-019, TC-025, TC-027, TC-029)
  - `test_file_upload.py` — file upload tests (TC-020, TC-024, TC-028)
  - `test_recording.py` — screen recording tests (TC-030 to TC-044)
  - `test_logs.py` — log download tests (TC-045)
  - `conftest.py` — pytest fixtures, config, and helpers
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
pip install -r FlintAPITest/EmulatorDeviceTest/requirements.txt
```

3. Configure environment variables in `FlintAPITest/EmulatorDeviceTest/test.env`:

```bash
FLINT_BASE_URL="https://staging.api.flintlab.io"   # change to your environment
FLINT_AUTH_TOKEN="Bearer <your-pat-token>"
FLINT_TEST_APK_PATH="/path/to/your/test-app.apk"   # required for TC-025, TC-029; auto-skipped if not set
FLINT_TEST_UPLOAD_FILE_PATH="/path/to/any/file"    # required for TC-020, TC-024; auto-skipped if not set
```

## Running the tests

From the repository root using the helper script:

```bash
chmod +x RunScripts/EmulatorDeviceTest.sh
./RunScripts/EmulatorDeviceTest.sh
```

Or run directly from the test folder:

```bash
cd FlintAPITest/EmulatorDeviceTest
chmod +x run_tests.sh
./run_tests.sh
```

Run a specific test by ID:

```bash
./RunScripts/EmulatorDeviceTest.sh -k TC-024
```

## Reports

After the run completes, reports are generated inside `FlintAPITest/EmulatorDeviceTest/`:

- `report.html` — standalone HTML report (open in any browser)
- `allure-report/index.html` — full Allure report (requires [Allure CLI](https://allurereport.org/docs/install/))

To open the Allure report:

```bash
allure open FlintAPITest/EmulatorDeviceTest/allure-report
```
