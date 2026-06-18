# Appium URL Test

This document describes the Appium URL E2E tests, prerequisites, and step-by-step instructions to run the tests locally.

## Overview

The Appium URL test suite validates the **Appium automation URL** issued by FlintAPI — its allocation, connection, expiry, isolation, reliability, scaling, and observability. FlintAPI is treated as a trusted upstream; these tests assert on the **URL and the session lifecycle it drives**, not FlintAPI internals. Tests are implemented in Python using `pytest` and live in the `FlintAPITest/AppiumURLTest/` directory.

Every run fetches a **real, fresh Appium URL** from FlintAPI. Negative / security / reliability cases derive controlled variants from that real URL (tamper the token, swap the host, call after release, cross-use between two users). OS/device is selected purely via Appium **capabilities** — the URL is identical for Android and iOS.

## Prerequisites

- Python 3.10+ installed, virtual environment recommended
- Git (to clone/update the repository)
- A valid FlintAPI Personal Access (NAT) token
- For the connect/run tests: a reachable Appium server and (for Android) `ANDROID_HOME` + SDK on the host

## Repository layout

- `FlintAPITest/AppiumURLTest/` — test sources
  - `test_allocation.py` — allocate / connect / unique URL (TC-001, 002, 004, 011, 012, 029)
  - `test_expiry.py` — expiry metadata, idle timeout, long-running (TC-003, 008, 009)
  - `test_security.py` — isolation, guessability, post-quit, invalid NAT (TC-006, 007, 013, 015)
  - `test_validation.py` — capability mismatch caught early (TC-005)
  - `test_concurrency.py` — parallel isolation, race, caps (TC-014, 016, 020, 026)
  - `test_reliability.py` — GC sweep + fault tolerance (TC-010, 019, 022, 023, 025, 028)
  - `test_scalability.py` — pool boundary, load ramp, scale-out (TC-017, 018, 024)
  - `test_observability.py` — rate limiting + metrics (TC-027, 030)
  - `conftest.py` — config, HTTP clients, allocate/release/connect + URL-mutation helpers
  - `requirements.txt` — Python dependencies
  - `test.env` — environment variables (secrets/config/thresholds)


## Setup

1. Create and activate a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install Python dependencies:

```bash
pip install --upgrade pip
pip install -r FlintAPITest/AppiumURLTest/requirements.txt
```

3. Configure environment variables in `FlintAPITest/AppiumURLTest/test.env`:

```bash
FLINT_BASE_URL="https://staging.api.flintlab.io"   # change to your environment
FLINT_AUTH_TOKEN="Bearer <your-nat-token>"          # NAT token, sent on every request
FLINT_AUTH_TOKEN_B="Bearer <second-user-token>"     # required for TC-006, TC-014
FLINT_SURFACE="emulator"                            # emulator | physical
FLINT_PHYSICAL_DEVICE_ID="<device-id>"              # required when FLINT_SURFACE=physical
```

Thresholds (cold-start window, idle grace, pool size, concurrency cap, GC interval,
rate limit) are also in `test.env` — **no test hardcodes them.**

## Running the tests

From the repository root using the helper script:

```bash
chmod +x RunScripts/AppiumURLTest.sh
./RunScripts/AppiumURLTest.sh
```

Or run directly from the test folder:

```bash
cd FlintAPITest/AppiumURLTest
chmod +x run_tests.sh
./run_tests.sh
```

Useful slices:

```bash
./RunScripts/AppiumURLTest.sh -k TC-006        # one test by ID
./RunScripts/AppiumURLTest.sh -m security      # one category
./RunScripts/AppiumURLTest.sh --env staging    # include destructive tests
```

### Safety: the `--env` gate

Destructive tests (`@pytest.mark.destructive`) break the server/host on purpose
(network drop, Appium crash, node drain, control-plane restart). They run **only**
with `--env staging`; on `preprod` (default) they skip, and on `production` they are
hard-blocked. The faults themselves are driven by operator commands supplied in
`test.env` (`FAULT_*`) so no destructive shell ships in code — a case skips if its
command is unset.

## Reports

After the run completes, reports are generated inside `FlintAPITest/AppiumURLTest/`:

- `report.html` — standalone HTML report (open in any browser)
- `allure-report/index.html` — full Allure report (requires [Allure CLI](https://allurereport.org/docs/install/))

To open the Allure report:

```bash
allure open FlintAPITest/AppiumURLTest/allure-report
```
