Record and Upload Test Automation
Quick Start
1. Setup
bash
# Navigate to test directory
cd /home/gowtham-flint/Desktop/platform-auto/platform-automation/FlintAPITest/RecordAndUploadTest

# Copy and configure .env file
cp .env.example .env
# Edit .env and add your FLINT_API_TOKEN

# Install dependencies
pip install -r requirements.txt
2. Run Tests
bash
# From the RunScripts directory
cd /home/gowtham-flint/Desktop/platform-auto/platform-automation/RunScripts

# Run with interactive menu
./RecordAndUploadTest.sh

# Or run specific test suites directly
./RecordAndUploadTest.sh android      # Android Recording & APK Upload
./RecordAndUploadTest.sh ios          # iOS IPA Upload
./RecordAndUploadTest.sh emulator     # Emulator Recording & APK Upload
./RecordAndUploadTest.sh all          # Run all tests
./RecordAndUploadTest.sh html         # Run all tests with HTML report
3. Menu Options
text
============================================================
🚀 RECORD & UPLOAD TEST MENU
============================================================
1) Android - Recording & APK Upload
2) iOS - IPA Upload
3) Emulators - Recording & APK Upload
4) Run All Tests
5) Run All Tests with HTML Report
6) Exit
============================================================
Enter choice [1-6]:
4. Requirements
Requirement	Details
Python	3.8+
Token	Valid FLINT_API_TOKEN in .env
Test Files	.apk and .ipa files in test_files/ directory
Devices	At least one device/emulator available
5. Files Location
text
platform-automation/
├── FlintAPITest/
│   └── RecordAndUploadTest/
│       ├── .env                      # ⚙️ Configuration (add your token)
│       ├── requirements.txt          # 📦 Dependencies
│       ├── record_and_upload_test.py # 📱 Android tests
│       ├── ios_device_upload.py      # 🍎 iOS tests
│       ├── emulator_record_upload_test.py # 🤖 Emulator tests
│       └── test_files/               # 📁 Place APK/IPA files here
│           ├── BitBarSampleApp.apk
│           └── sample.ipa
└── RunScripts/
    └── RecordAndUploadTest.sh        # 🚀 Test runner script
6. Example
bash
# Step 1: Navigate to RunScripts
cd /home/gowtham-flint/Desktop/platform-auto/platform-automation/RunScripts

# Step 2: Make script executable (first time only)
chmod +x RecordAndUploadTest.sh

# Step 3: Run tests
./RecordAndUploadTest.sh

# Step 4: Select option 1 for Android tests
# Or option 2 for iOS, option 3 for Emulator
7. Troubleshooting
Issue	Solution
.env file not found	Create .env in RecordAndUploadTest/ directory
Token not set	Add FLINT_API_TOKEN=your_token to .env
No APK file	Place .apk in test_files/ directory
No devices available	Ensure devices/emulators are online
Permission denied	Run chmod +x RecordAndUploadTest.sh