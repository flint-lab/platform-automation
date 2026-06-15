# FlintLab Log Automation

Automation scripts for Physical Device and Emulator log testing.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file from example
cp .env.example .env

# 3. Edit .env and add your token
# FLINT_API_TOKEN=your_token_here
Run Tests
Physical Device Test
bash
python device_log_test.py
Emulator Test
bash
python emulator_log_test.py
Files
File	Description
device_log_test.py	Physical device log query tests
emulator_log_test.py	Emulator log download tests
.env	Configuration (API URL, token, wait time)
requirements.txt	Python dependencies
Environment Variables (.env)
text
FLINT_API_BASE=https://staging.api.flintlab.io
FLINT_API_TOKEN=your_token_here
WAIT_TIME_FOR_LOGS=20
LOG_QUERY_MINUTES=10
SEARCH_KEYWORD=device