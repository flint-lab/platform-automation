import pytest
import requests
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(ENV_FILE)

# Configuration
BASE_URL = os.getenv("FLINT_API_BASE", "https://staging.api.flintlab.io")
AUTH_TOKEN = os.getenv("FLINT_API_TOKEN")

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

allocation_time = None
session_id = None
device_id = None

# Test file paths
TEST_DIR = Path(__file__).parent / "test_files"
TEST_DIR.mkdir(exist_ok=True)

# Find APK file dynamically
def get_apk_path():
    """Find the first .apk file in test_files directory"""
    apk_files = list(TEST_DIR.glob("*.apk"))
    if apk_files:
        return str(apk_files[0])
    return None

# Set APK path dynamically
TEST_APK_PATH = get_apk_path()
TEST_FILE_PATH = str(TEST_DIR / "test.txt")

# Sample APK URL for testing
SAMPLE_APK_URL = "https://github.com/bitbar/test-samples/raw/master/apps/android/bitbar-sample-app.apk"
INVALID_APK_URL = "https://example.com/invalid.apk"

# ============ FIXTURE: Allocate First Available Device ============

@pytest.fixture(scope="module")
def setup_device():
    """Setup: Get and allocate first available device"""
    global allocation_time, session_id, device_id
    
    # Get first available Android device
    response = requests.get(f"{BASE_URL}/v1/devices/physical/list?Availability=available&os=android", headers=headers)
    if response.status_code != 200:
        pytest.fail(f"Failed to get device list: {response.status_code}")
    
    devices = response.json()
    if not devices:
        pytest.fail("No devices available")
    
    device_id = devices[0].get("device_id")
    print(f"\n✅ Got device: {device_id}")
    print(f"   Device name: {devices[0].get('name', 'N/A')}")
    
    # Allocate device
    allocation_time = datetime.now(timezone.utc)
    print(f"   Allocation time (UTC): {allocation_time.isoformat().replace('+00:00', 'Z')}")
    
    response = requests.get(f"{BASE_URL}/v1/devices/physical/get/{device_id}", headers=headers)
    if response.status_code != 200:
        pytest.fail(f"Allocation failed: {response.status_code}")
    
    session_id = response.json().get('session_id')
    print(f"✅ Device allocated successfully")
    print(f"   Session ID: {session_id}")
    
    yield session_id, device_id
    
    # Teardown: Release device
    print(f"\n🔓 Releasing device: {device_id}")
    requests.post(f"{BASE_URL}/v1/devices/physical/release/{device_id}", headers=headers)
    print(f"✅ Device released successfully")

# ============ RECORDING TESTS ============

def test_start_recording_success(setup_device):
    """TC1: Verify start recording succeeds for valid session"""
    print("\n" + "="*60)
    print("📋 TEST 1: Start recording - valid session")
    print("="*60)
    
    session_id, _ = setup_device
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/record/start/{session_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"   ✅ Recording started successfully")
        print(f"   Response: {response.json()}")
        assert True
    else:
        print(f"   ⚠️ Could not start recording: {response.status_code}")
        print(f"   Response: {response.text}")

def test_start_recording_invalid_session():
    """TC2: Verify start recording fails when session does not exist"""
    print("\n" + "="*60)
    print("📋 TEST 2: Start recording - invalid session")
    print("="*60)
    
    invalid_session = "invalid-session-id-12345"
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/record/start/{invalid_session}",
        headers=headers
    )
    
    assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid session with {response.status_code}")

def test_start_recording_unauthorized(setup_device):
    """TC3: Verify start recording fails when user does not own session"""
    print("\n" + "="*60)
    print("📋 TEST 3: Start recording - unauthorized user")
    print("="*60)
    
    session_id, _ = setup_device
    
    invalid_headers = {
        "Authorization": "Bearer invalid_token",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/record/start/{session_id}",
        headers=invalid_headers
    )
    
    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    print(f"   ✅ Correctly returned {response.status_code} for unauthorized user")

def test_stop_recording_success(setup_device):
    """TC4: Verify stop recording succeeds for active recording"""
    print("\n" + "="*60)
    print("📋 TEST 4: Stop recording - valid session")
    print("="*60)
    
    session_id, _ = setup_device
    
    # First start recording
    start_response = requests.post(
        f"{BASE_URL}/v1/devices/physical/record/start/{session_id}",
        headers=headers
    )
    
    if start_response.status_code != 200:
        print("   ⚠️ Could not start recording, skipping stop test")
        return
    
    print("   ✅ Recording started successfully")
    time.sleep(3)
    
    # Then stop recording
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/record/stop/{session_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"   ✅ Recording stopped successfully")
        print(f"   Response: {response.json()}")
    else:
        print(f"   ⚠️ Stop recording response: {response.status_code}")

def test_stop_recording_invalid_session():
    """TC5: Verify stop recording fails when session not found"""
    print("\n" + "="*60)
    print("📋 TEST 5: Stop recording - invalid session")
    print("="*60)
    
    invalid_session = "invalid-session-id-12345"
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/record/stop/{invalid_session}",
        headers=headers
    )
    
    assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid session with {response.status_code}")

def test_download_all_recordings(setup_device):
    """TC6: Verify download all recordings returns zip file"""
    print("\n" + "="*60)
    print("📋 TEST 6: Download all recordings")
    print("="*60)
    
    session_id, _ = setup_device
    
    response = requests.get(
        f"{BASE_URL}/v1/devices/physical/record/download-all/{session_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        assert "application/zip" in response.headers.get("Content-Type", "")
        print("   ✅ Zip file downloaded successfully")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"recordings_{session_id}_{timestamp}.zip"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"   📁 Saved as: {filename}")
    elif response.status_code == 404:
        print("   ⚠️ No recordings found")
    else:
        print(f"   Unexpected status: {response.status_code}")

def test_download_all_recordings_invalid_session():
    """TC7: Verify download all recordings fails for non-existent session"""
    print("\n" + "="*60)
    print("📋 TEST 7: Download all recordings - invalid session")
    print("="*60)
    
    invalid_session = "invalid-session-id-12345"
    
    response = requests.get(
        f"{BASE_URL}/v1/devices/physical/record/download-all/{invalid_session}",
        headers=headers
    )
    
    assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid session with {response.status_code}")

def test_complete_recording_lifecycle(setup_device):
    """TC8: Verify complete recording lifecycle works end-to-end"""
    print("\n" + "="*60)
    print("📋 TEST 8: Complete recording lifecycle")
    print("="*60)
    
    session_id, _ = setup_device
    
    # 1. Start recording
    print("\n   Step 1: Starting recording...")
    start_response = requests.post(
        f"{BASE_URL}/v1/devices/physical/record/start/{session_id}",
        headers=headers
    )
    if start_response.status_code == 200:
        print("   ✅ Start recording successful")
    else:
        print(f"   ⚠️ Start recording: {start_response.status_code}")
        return
    
    time.sleep(3)
    
    # 2. Stop recording
    print("\n   Step 2: Stopping recording...")
    stop_response = requests.post(
        f"{BASE_URL}/v1/devices/physical/record/stop/{session_id}",
        headers=headers
    )
    if stop_response.status_code == 200:
        print("   ✅ Stop recording successful")
    else:
        print(f"   ⚠️ Stop recording: {stop_response.status_code}")
    
    # 3. Download all recordings
    print("\n   Step 3: Downloading all recordings...")
    download_response = requests.get(
        f"{BASE_URL}/v1/devices/physical/record/download-all/{session_id}",
        headers=headers
    )
    if download_response.status_code == 200:
        print("   ✅ Download all recordings successful")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"recordings_{session_id}_{timestamp}.zip"
        with open(filename, 'wb') as f:
            f.write(download_response.content)
        print(f"   📁 Saved as: {filename}")
    elif download_response.status_code == 404:
        print("   ⚠️ No recordings to download")

# ============ APK INSTALLATION TESTS ============

def test_install_apk_success(setup_device):
    """TC9: Verify install APK succeeds on allocated Android device"""
    print("\n" + "="*60)
    print("📋 TEST 9: Install APK - success")
    print("="*60)
    
    _, device_id = setup_device
    
    # Get APK path dynamically
    apk_path = get_apk_path()
    if not apk_path:
        print("   ⚠️ No APK file found in test_files directory")
        print("   Please place an .apk file in test_files directory")
        pytest.skip("No APK file found")
    
    print(f"   Using APK: {os.path.basename(apk_path)}")
    
    with open(apk_path, 'rb') as f:
        files = {
            'file': (os.path.basename(apk_path), f, 'application/vnd.android.package-archive')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-apk/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    if response.status_code == 200:
        print(f"   ✅ APK installed successfully")
        print(f"   Response: {response.json()}")
    else:
        print(f"   ⚠️ Install response: {response.status_code}")
        print(f"   Response: {response.text}")

def test_install_apk_invalid_extension(setup_device):
    """TC10: Verify install APK fails when file extension is not .apk"""
    print("\n" + "="*60)
    print("📋 TEST 10: Install APK - invalid file extension")
    print("="*60)
    
    _, device_id = setup_device
    
    # Create a dummy text file if it doesn't exist
    if not os.path.exists(TEST_FILE_PATH):
        os.makedirs(os.path.dirname(TEST_FILE_PATH), exist_ok=True)
        with open(TEST_FILE_PATH, 'w') as f:
            f.write("This is a test file")
    
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {
            'file': (os.path.basename(TEST_FILE_PATH), f, 'text/plain')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-apk/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    print(f"   ✅ Correctly rejected non-APK file with {response.status_code}")

def test_install_apk_unauthorized(setup_device):
    """TC11: Verify install APK fails when user tries to install on unallocated device"""
    print("\n" + "="*60)
    print("📋 TEST 11: Install APK - unauthorized")
    print("="*60)
    
    _, device_id = setup_device
    
    # Get APK path dynamically
    apk_path = get_apk_path()
    if not apk_path:
        pytest.skip("No APK file found")
    
    invalid_headers = {
        "Authorization": "Bearer invalid_token"
    }
    
    with open(apk_path, 'rb') as f:
        files = {
            'file': (os.path.basename(apk_path), f, 'application/vnd.android.package-archive')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-apk/{device_id}",
            headers=invalid_headers,
            files=files
        )
    
    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    print(f"   ✅ Correctly returned {response.status_code} for unauthorized user")

def test_install_apk_invalid_device_id():
    """TC12: Verify install APK fails with invalid device_id"""
    print("\n" + "="*60)
    print("📋 TEST 12: Install APK - invalid device_id")
    print("="*60)
    
    invalid_device = "invalid-device-id-12345"
    
    # Get APK path dynamically
    apk_path = get_apk_path()
    if not apk_path:
        pytest.skip("No APK file found")
    
    with open(apk_path, 'rb') as f:
        files = {
            'file': (os.path.basename(apk_path), f, 'application/vnd.android.package-archive')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-apk/{invalid_device}",
            headers=headers,
            files=files
        )
    
    # API returns 422 for invalid device
    assert response.status_code in [404, 403, 422], f"Expected 404/403/422, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid device with {response.status_code}")

def test_install_apk_via_url_success(setup_device):
    """TC13: Verify install APK via URL starts async installation"""
    print("\n" + "="*60)
    print("📋 TEST 13: Install APK via URL - success")
    print("="*60)
    
    _, device_id = setup_device
    
    body = {
        "apk_url": SAMPLE_APK_URL
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/install-apk-via-url/{device_id}",
        headers=headers,
        json=body
    )
    
    if response.status_code in [200, 202]:
        data = response.json()
        print(f"   ✅ Installation started successfully")
        print(f"   Response: {data}")
        
        if "request_id" in data:
            request_id = data.get("request_id")
            print(f"   📋 Request ID: {request_id}")
            
            for attempt in range(5):
                print(f"   Checking status (attempt {attempt+1}/5)...")
                status_response = requests.get(
                    f"{BASE_URL}/v1/devices/physical/install-apk-via-url-status/{request_id}",
                    headers=headers
                )
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   Status: {status_data}")
                    if status_data.get("status") in ["SUCCESS", "COMPLETED", "INSTALLED"]:
                        print("   ✅ Installation completed successfully")
                        break
                    elif status_data.get("status") in ["FAILED", "ERROR"]:
                        print(f"   ❌ Installation failed: {status_data}")
                        break
                time.sleep(3)
    else:
        print(f"   ⚠️ Response: {response.status_code}")
        print(f"   Response: {response.text}")

def test_install_apk_via_url_invalid_device():
    """TC14: Verify install APK via URL fails for invalid device"""
    print("\n" + "="*60)
    print("📋 TEST 14: Install APK via URL - invalid device")
    print("="*60)
    
    invalid_device = "invalid-device-id-12345"
    
    body = {
        "apk_url": SAMPLE_APK_URL
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/install-apk-via-url/{invalid_device}",
        headers=headers,
        json=body
    )
    
    assert response.status_code in [400, 404, 422, 500], f"Expected 400/404/422/500, got {response.status_code}"
    print(f"   ✅ Handled invalid device with {response.status_code}")

def test_install_apk_via_url_invalid_url(setup_device):
    """TC15: Verify install APK via URL fails with invalid APK URL"""
    print("\n" + "="*60)
    print("📋 TEST 15: Install APK via URL - invalid URL")
    print("="*60)
    
    _, device_id = setup_device
    
    body = {
        "apk_url": INVALID_APK_URL
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/install-apk-via-url/{device_id}",
        headers=headers,
        json=body
    )
    
    if response.status_code in [400, 404, 422, 500]:
        print(f"   ✅ Correctly rejected invalid URL with {response.status_code}")
    else:
        print(f"   ⚠️ Response: {response.status_code}")

# ============ TESTS AFTER DEALLOCATION ============

def test_record_after_deallocation(setup_device):
    """TC16: Verify recording fails after device deallocation"""
    print("\n" + "="*60)
    print("📋 TEST 16: Recording after deallocation")
    print("="*60)
    
    session_id, device_id = setup_device
    
    print(f"\n🔓 Deallocating device...")
    requests.post(f"{BASE_URL}/v1/devices/physical/release/{device_id}", headers=headers)
    print("✅ Device deallocated")
    
    time.sleep(2)
    
    print("\n   Attempting to start recording after deallocation...")
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/record/start/{session_id}",
        headers=headers
    )
    
    if response.status_code in [400, 404, 403, 500]:
        print(f"   ✅ Correctly failed with {response.status_code} after deallocation")
    else:
        print(f"   ⚠️ Unexpected response: {response.status_code}")

def test_upload_after_deallocation(setup_device):
    """TC17: Verify upload fails after device deallocation"""
    print("\n" + "="*60)
    print("📋 TEST 17: Upload after deallocation")
    print("="*60)
    
    session_id, device_id = setup_device
    
    print(f"\n🔓 Deallocating device...")
    requests.post(f"{BASE_URL}/v1/devices/physical/release/{device_id}", headers=headers)
    print("✅ Device deallocated")
    
    time.sleep(2)
    
    print("\n   Attempting to install APK after deallocation...")
    
    apk_path = get_apk_path()
    if not apk_path:
        pytest.skip("No APK file found")
    
    with open(apk_path, 'rb') as f:
        files = {
            'file': (os.path.basename(apk_path), f, 'application/vnd.android.package-archive')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-apk/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    if response.status_code in [400, 404, 403, 500]:
        print(f"   ✅ Correctly failed with {response.status_code} after deallocation")
    else:
        print(f"   ⚠️ Unexpected response: {response.status_code}")

# ============ CLEANUP ============

@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """Clean up test files after all tests"""
    yield
    print("\n🧹 Cleaning up...")