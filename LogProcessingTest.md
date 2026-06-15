# FlintLab Log Automation

Automation scripts for Physical Device and Emulator log testing using pytest.

## Prerequisites

- Python 3.8+
- pip
- Virtual environment (optional but recommended)

## Setup

```bash
# 1. Clone the repository and navigate to LogProcessingTest directory
cd FlintAPITest/LogProcessingTest

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file from example
cp .env.example .env

# 4. Edit .env and add your token
# FLINT_API_TOKEN=your_token_here
Go to RunScripts folder
Running Tests
Using Shell Script (Recommended)
The run script is located at RunScripts/LogProcessingTest.sh

bash
# From anywhere in the project
bash RunScripts/LogProcessingTest.sh

# Or with specific modes
bash RunScripts/LogProcessingTest.sh physical    # Run physical device tests only
bash RunScripts/LogProcessingTest.sh emulator    # Run emulator tests only
bash RunScripts/LogProcessingTest.sh both        # Run both tests
bash RunScripts/LogProcessingTest.sh html        # Run both tests with HTML report
Interactive Menu
When running without arguments, you'll see:

text
============================================================
Select test to run:
============================================================
1) Physical Device Test
2) Emulator Test
3) Run Both Tests
4) Run Both Tests with HTML Report
5) Exit
============================================================
Enter choice [1-5]:
Running Directly with pytest
bash
# Physical device tests
pytest device_log_test.py -v -s

# Emulator tests
pytest emulator_log_test.py -v -s

# Both tests with HTML report
pytest device_log_test.py emulator_log_test.py -v -s --html=report.html --self-contained-html
Test Reports
HTML reports are automatically saved to TestReports/ directory when running with html mode:

text
TestReports/
└── LogProcessingTest_Report_2024-01-01_12-00-00.html