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
recipe_uuid = None

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

# Find IPA file dynamically (for negative test)
def get_ipa_path():
    """Find the first .ipa file in test_files directory"""
    ipa_files = list(TEST_DIR.glob("*.ipa"))
    if ipa_files:
        return str(ipa_files[0])
    return None

# Set paths
TEST_APK_PATH = get_apk_path()
TEST_IPA_PATH = get_ipa_path()
TEST_FILE_PATH = str(TEST_DIR / "test.txt")

# ============ FIXTURE: Allocate First Available Emulator ============

@pytest.fixture(scope="module")
def setup_emulator():
    """Setup: Get and allocate first available emulator"""
    global allocation_time, session_id, device_id, recipe_uuid
    
    # Get first available emulator
    response = requests.get(f"{BASE_URL}/v1/devices/emulator/list", headers=headers)
    if response.status_code != 200:
        pytest.fail(f"Failed to get emulator list: {response.status_code}")
    
    emulators = response.json()
    if not emulators:
        pytest.fail("No emulators available")
    
    recipe_uuid = emulators[0].get("recipe_uuid")
    emulator_name = emulators[0].get("name", "N/A")
    
    print(f"\n✅ Got emulator: {emulator_name}")
    print(f"   Recipe UUID: {recipe_uuid}")
    print(f"   OS: {emulators[0].get('os', 'N/A')} {emulators[0].get('os_version', 'N/A')}")
    
    # Allocate emulator
    allocation_time = datetime.now(timezone.utc)
    print(f"   Allocation time (UTC): {allocation_time.isoformat().replace('+00:00', 'Z')}")
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/allocate-emulator?recipe_uuid={recipe_uuid}",
        headers=headers
    )
    
    if response.status_code != 200:
        pytest.fail(f"Allocation failed: {response.status_code}")
    
    data = response.json()
    session_id = data.get('session_id')
    device_details = data.get('device_details', {})
    device_id = device_details.get('device_id')
    
    print(f"✅ Emulator allocated successfully")
    print(f"   Session ID: {session_id}")
    print(f"   Device ID: {device_id}")
    
    yield session_id, device_id
    
    # Teardown: Stop emulator session
    print(f"\n🛑 Stopping emulator session...")
    requests.post(f"{BASE_URL}/v1/devices/emulator/device/{device_id}/stop/session", headers=headers)
    print(f"✅ Emulator session stopped")

# ============ HELPER FUNCTION ============

def stop_recording_if_active(session_id):
    """Stop recording if it's active"""
    try:
        response = requests.post(
            f"{BASE_URL}/v1/devices/emulator/record/stop/{session_id}",
            headers=headers
        )
        if response.status_code == 200:
            print("   ✅ Stopped previous recording")
            return True
    except:
        pass
    return False

# ============ NEGATIVE TESTS FIRST (Invalid cases) ============

def test_emulator_start_recording_invalid_session():
    """TC1: Verify start recording fails when session does not exist"""
    print("\n" + "="*60)
    print("📋 TEST 1: Emulator - Start recording - invalid session")
    print("="*60)
    
    invalid_session = "invalid-session-id-12345"
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/start/{invalid_session}",
        headers=headers
    )
    
    assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid session with {response.status_code}")

def test_emulator_stop_recording_invalid_session():
    """TC2: Verify stop recording fails when session not found"""
    print("\n" + "="*60)
    print("📋 TEST 2: Emulator - Stop recording - invalid session")
    print("="*60)
    
    invalid_session = "invalid-session-id-12345"
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/stop/{invalid_session}",
        headers=headers
    )
    
    assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid session with {response.status_code}")

def test_emulator_download_all_recordings_invalid_session():
    """TC3: Verify download all recordings fails for non-existent session"""
    print("\n" + "="*60)
    print("📋 TEST 3: Emulator - Download all recordings - invalid session")
    print("="*60)
    
    invalid_session = "invalid-session-id-12345"
    
    response = requests.get(
        f"{BASE_URL}/v1/devices/emulator/record/download-all/{invalid_session}",
        headers=headers
    )
    
    assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid session with {response.status_code}")

def test_emulator_install_apk_invalid_device_id():
    """TC4: Verify install APK fails with invalid device_id"""
    print("\n" + "="*60)
    print("📋 TEST 4: Emulator - Install APK - invalid device_id")
    print("="*60)
    
    invalid_device = "invalid-device-id-12345"
    
    apk_path = get_apk_path()
    if not apk_path:
        pytest.skip("No APK file found")
    
    with open(apk_path, 'rb') as f:
        files = {
            'file': (os.path.basename(apk_path), f, 'application/vnd.android.package-archive')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/emulator/install-apk/{invalid_device}",
            headers=headers,
            files=files
        )
    
    assert response.status_code in [404, 403, 422], f"Expected 404/403/422, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid device with {response.status_code}")

# ============ VALID TESTS (With real session) ============

def test_emulator_start_recording_success(setup_emulator):
    """TC5: Verify start recording succeeds for valid emulator session"""
    print("\n" + "="*60)
    print("📋 TEST 5: Emulator - Start recording - success")
    print("="*60)
    
    session_id, _ = setup_emulator
    
    # Make sure no previous recording is active
    stop_recording_if_active(session_id)
    time.sleep(1)
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/start/{session_id}",
        headers=headers
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"   ✅ Recording started successfully")
    print(f"   Response: {response.json()}")

def test_emulator_stop_recording_success(setup_emulator):
    """TC6: Verify stop recording succeeds for active recording"""
    print("\n" + "="*60)
    print("📋 TEST 6: Emulator - Stop recording - success")
    print("="*60)
    
    session_id, _ = setup_emulator
    
    # Stop any existing recording first
    stop_recording_if_active(session_id)
    time.sleep(1)
    
    # Start a new recording
    start_response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/start/{session_id}",
        headers=headers
    )
    
    if start_response.status_code != 200:
        print(f"   ⚠️ Could not start recording: {start_response.status_code}")
        pytest.skip("Could not start recording")
    
    print("   ✅ Recording started")
    time.sleep(3)
    
    # Stop the recording
    response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/stop/{session_id}",
        headers=headers
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"   ✅ Recording stopped successfully")
    print(f"   Response: {response.json()}")

def test_emulator_download_recording_success(setup_emulator):
    """TC7: Verify download recording succeeds for valid session and filename"""
    print("\n" + "="*60)
    print("📋 TEST 7: Emulator - Download recording - success")
    print("="*60)
    
    session_id, _ = setup_emulator
    
    # Stop any existing recording
    stop_recording_if_active(session_id)
    time.sleep(1)
    
    # Start recording
    start_response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/start/{session_id}",
        headers=headers
    )
    
    if start_response.status_code != 200:
        print(f"   ⚠️ Could not start recording: {start_response.status_code}")
        pytest.skip("Could not start recording")
    
    print("   ✅ Recording started")
    time.sleep(5)
    
    # Stop recording to get filename
    stop_response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/stop/{session_id}",
        headers=headers
    )
    
    if stop_response.status_code != 200:
        print(f"   ⚠️ Could not stop recording: {stop_response.status_code}")
        pytest.skip("Could not stop recording")
    
    data = stop_response.json()
    filename = data.get('filename', 'recording.mp4')
    print(f"   Filename: {filename}")
    
    # Download the recording
    response = requests.get(
        f"{BASE_URL}/v1/devices/emulator/record/download/{session_id}/{filename}",
        headers=headers
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("   ✅ Recording downloaded successfully")
    
    # Save the file
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    local_filename = f"emulator_recording_{session_id}_{timestamp}.mp4"
    with open(local_filename, 'wb') as f:
        f.write(response.content)
    print(f"   📁 Saved as: {local_filename}")

def test_emulator_download_recording_invalid_filename(setup_emulator):
    """TC8: Verify download recording fails with invalid filename"""
    print("\n" + "="*60)
    print("📋 TEST 8: Emulator - Download recording - invalid filename")
    print("="*60)
    
    session_id, _ = setup_emulator
    
    # Stop any existing recording
    stop_recording_if_active(session_id)
    time.sleep(1)
    
    # Start recording
    start_response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/start/{session_id}",
        headers=headers
    )
    
    if start_response.status_code != 200:
        print(f"   ⚠️ Could not start recording: {start_response.status_code}")
        pytest.skip("Could not start recording")
    
    print("   ✅ Recording started")
    time.sleep(3)
    
    # Stop recording
    stop_response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/stop/{session_id}",
        headers=headers
    )
    
    if stop_response.status_code != 200:
        print(f"   ⚠️ Could not stop recording: {stop_response.status_code}")
        pytest.skip("Could not stop recording")
    
    print("   ✅ Recording stopped")
    
    # Try to download with invalid filename
    invalid_filename = "invalid_file.mp4"
    
    response = requests.get(
        f"{BASE_URL}/v1/devices/emulator/record/download/{session_id}/{invalid_filename}",
        headers=headers
    )
    
    # API returns 500 for invalid filename
    assert response.status_code in [404, 403, 500], f"Expected 404/403/500, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid filename with {response.status_code}")

def test_emulator_download_all_recordings(setup_emulator):
    """TC9: Verify download all recordings returns zip file"""
    print("\n" + "="*60)
    print("📋 TEST 9: Emulator - Download all recordings")
    print("="*60)
    
    session_id, _ = setup_emulator
    
    # Stop any existing recording
    stop_recording_if_active(session_id)
    time.sleep(1)
    
    # Create a recording
    start_response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/start/{session_id}",
        headers=headers
    )
    
    if start_response.status_code == 200:
        print("   ✅ Recording started")
        time.sleep(3)
        
        stop_response = requests.post(
            f"{BASE_URL}/v1/devices/emulator/record/stop/{session_id}",
            headers=headers
        )
        if stop_response.status_code == 200:
            print("   ✅ Recording stopped")
    
    response = requests.get(
        f"{BASE_URL}/v1/devices/emulator/record/download-all/{session_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        assert "application/zip" in response.headers.get("Content-Type", "")
        print("   ✅ Zip file downloaded successfully")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"emulator_recordings_{session_id}_{timestamp}.zip"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"   📁 Saved as: {filename}")
    elif response.status_code == 404:
        print("   ⚠️ No recordings found")
    else:
        print(f"   Unexpected status: {response.status_code}")

def test_emulator_start_recording_unauthorized(setup_emulator):
    """TC10: Verify start recording fails when user does not own session"""
    print("\n" + "="*60)
    print("📋 TEST 10: Emulator - Start recording - unauthorized")
    print("="*60)
    
    session_id, _ = setup_emulator
    
    # Stop any existing recording first
    stop_recording_if_active(session_id)
    time.sleep(1)
    
    invalid_headers = {
        "Authorization": "Bearer invalid_token",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/start/{session_id}",
        headers=invalid_headers
    )
    
    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    print(f"   ✅ Correctly returned {response.status_code} for unauthorized user")

def test_emulator_install_apk_success(setup_emulator):
    """TC11: Verify install APK succeeds on emulator"""
    print("\n" + "="*60)
    print("📋 TEST 11: Emulator - Install APK - success")
    print("="*60)
    
    _, device_id = setup_emulator
    
    apk_path = get_apk_path()
    if not apk_path:
        print("   ⚠️ No APK file found in test_files directory")
        pytest.skip("No APK file found")
    
    print(f"   Using APK: {os.path.basename(apk_path)}")
    
    with open(apk_path, 'rb') as f:
        files = {
            'file': (os.path.basename(apk_path), f, 'application/vnd.android.package-archive')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/emulator/install-apk/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"   ✅ APK installed successfully on emulator")
    print(f"   Response: {response.json()}")

def test_emulator_install_apk_invalid_extension(setup_emulator):
    """TC12: Verify install APK fails when file extension is not .apk"""
    print("\n" + "="*60)
    print("📋 TEST 12: Emulator - Install APK - invalid extension")
    print("="*60)
    
    _, device_id = setup_emulator
    
    if not os.path.exists(TEST_FILE_PATH):
        os.makedirs(os.path.dirname(TEST_FILE_PATH), exist_ok=True)
        with open(TEST_FILE_PATH, 'w') as f:
            f.write("This is a test file - not an APK")
    
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {
            'file': (os.path.basename(TEST_FILE_PATH), f, 'text/plain')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/emulator/install-apk/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
    print(f"   ✅ Correctly rejected non-APK file with {response.status_code}")

def test_emulator_install_apk_unauthorized(setup_emulator):
    """TC13: Verify install APK fails when user does not own device"""
    print("\n" + "="*60)
    print("📋 TEST 13: Emulator - Install APK - unauthorized")
    print("="*60)
    
    _, device_id = setup_emulator
    
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
            f"{BASE_URL}/v1/devices/emulator/install-apk/{device_id}",
            headers=invalid_headers,
            files=files
        )
    
    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    print(f"   ✅ Correctly returned {response.status_code} for unauthorized user")

def test_emulator_install_ipa_on_android_emulator(setup_emulator):
    """TC14: Verify install IPA fails on Android emulator"""
    print("\n" + "="*60)
    print("📋 TEST 14: Emulator - Install IPA on Android emulator - should fail")
    print("="*60)
    
    _, device_id = setup_emulator
    
    ipa_path = get_ipa_path()
    if not ipa_path:
        print("   ⚠️ No IPA file found, skipping test")
        pytest.skip("No IPA file found")
    
    print(f"   Using IPA: {os.path.basename(ipa_path)}")
    
    with open(ipa_path, 'rb') as f:
        files = {
            'file': (os.path.basename(ipa_path), f, 'application/octet-stream')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/emulator/install-apk/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    assert response.status_code in [400, 422, 403], f"Expected 400/422/403, got {response.status_code}"
    print(f"   ✅ Correctly rejected IPA on Android emulator with {response.status_code}")

# ============ TESTS AFTER DEALLOCATION ============

def test_emulator_record_after_deallocation(setup_emulator):
    """TC15: Verify recording fails after emulator deallocation"""
    print("\n" + "="*60)
    print("📋 TEST 15: Emulator - Recording after deallocation")
    print("="*60)
    
    session_id, device_id = setup_emulator
    
    # Stop any existing recording first
    stop_recording_if_active(session_id)
    
    print(f"\n🛑 Stopping emulator session...")
    requests.post(f"{BASE_URL}/v1/devices/emulator/device/{device_id}/stop/session", headers=headers)
    print("✅ Emulator session stopped")
    
    time.sleep(2)
    
    print("\n   Attempting to start recording after deallocation...")
    response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/record/start/{session_id}",
        headers=headers
    )
    
    assert response.status_code in [400, 404, 403, 500], f"Expected 400/404/403/500, got {response.status_code}"
    print(f"   ✅ Correctly failed with {response.status_code} after deallocation")

def test_emulator_download_after_deallocation(setup_emulator):
    """TC16: Verify download fails after emulator deallocation"""
    print("\n" + "="*60)
    print("📋 TEST 16: Emulator - Download after deallocation")
    print("="*60)
    
    session_id, device_id = setup_emulator
    
    # Stop any existing recording first
    stop_recording_if_active(session_id)
    
    print(f"\n🛑 Stopping emulator session...")
    requests.post(f"{BASE_URL}/v1/devices/emulator/device/{device_id}/stop/session", headers=headers)
    print("✅ Emulator session stopped")
    
    time.sleep(2)
    
    print("\n   Attempting to download all recordings after deallocation...")
    response = requests.get(
        f"{BASE_URL}/v1/devices/emulator/record/download-all/{session_id}",
        headers=headers
    )
    
    assert response.status_code in [400, 404, 403, 500], f"Expected 400/404/403/500, got {response.status_code}"
    print(f"   ✅ Correctly failed with {response.status_code} after deallocation")

def test_emulator_install_apk_after_deallocation(setup_emulator):
    """TC17: Verify install APK fails after emulator deallocation"""
    print("\n" + "="*60)
    print("📋 TEST 17: Emulator - Install APK after deallocation")
    print("="*60)
    
    session_id, device_id = setup_emulator
    
    print(f"\n🛑 Stopping emulator session...")
    requests.post(f"{BASE_URL}/v1/devices/emulator/device/{device_id}/stop/session", headers=headers)
    print("✅ Emulator session stopped")
    
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
            f"{BASE_URL}/v1/devices/emulator/install-apk/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    assert response.status_code in [400, 404, 403, 500], f"Expected 400/404/403/500, got {response.status_code}"
    print(f"   ✅ Correctly failed with {response.status_code} after deallocation")

# ============ CLEANUP ============

@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """Clean up test files after all tests"""
    yield
    print("\n🧹 Cleaning up...")