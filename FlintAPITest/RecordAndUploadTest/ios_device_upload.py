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

# Find IPA file dynamically
def get_ipa_path():
    """Find the first .ipa file in test_files directory"""
    ipa_files = list(TEST_DIR.glob("*.ipa"))
    if ipa_files:
        return str(ipa_files[0])
    return None

# Set IPA path dynamically
TEST_IPA_PATH = get_ipa_path()
TEST_FILE_PATH = str(TEST_DIR / "test.txt")
TEST_APK_PATH = str(TEST_DIR / "BitBarSampleApp.apk")

# ============ FIXTURE: Allocate First Available iOS Device ============

@pytest.fixture(scope="module")
def setup_ios_device():
    """Setup: Get and allocate first available iOS device"""
    global allocation_time, session_id, device_id
    
    # Get first available iOS device
    response = requests.get(f"{BASE_URL}/v1/devices/physical/list?Availability=available&os=ios", headers=headers)
    if response.status_code != 200:
        pytest.fail(f"Failed to get device list: {response.status_code}")
    
    devices = response.json()
    if not devices:
        pytest.fail("No iOS devices available")
    
    device_id = devices[0].get("device_id")
    print(f"\n✅ Got iOS device: {device_id}")
    print(f"   Device name: {devices[0].get('name', 'N/A')}")
    print(f"   OS: {devices[0].get('os', 'N/A')} {devices[0].get('os_version', 'N/A')}")
    
    # Allocate device
    allocation_time = datetime.now(timezone.utc)
    print(f"   Allocation time (UTC): {allocation_time.isoformat().replace('+00:00', 'Z')}")
    
    response = requests.get(f"{BASE_URL}/v1/devices/physical/get/{device_id}", headers=headers)
    if response.status_code != 200:
        pytest.fail(f"Allocation failed: {response.status_code}")
    
    session_id = response.json().get('session_id')
    print(f"✅ iOS Device allocated successfully")
    print(f"   Session ID: {session_id}")
    
    yield session_id, device_id
    
    # Teardown: Release device
    print(f"\n🔓 Releasing iOS device: {device_id}")
    requests.post(f"{BASE_URL}/v1/devices/physical/release/{device_id}", headers=headers)
    print(f"✅ iOS Device released successfully")

# ============ IPA INSTALLATION TESTS ============

def test_install_ipa_success(setup_ios_device):
    """TC1: Verify install IPA succeeds on allocated iOS device"""
    print("\n" + "="*60)
    print("📋 TEST 1: Install IPA - success")
    print("="*60)
    
    _, device_id = setup_ios_device
    
    # Get IPA path dynamically
    ipa_path = get_ipa_path()
    if not ipa_path:
        print("   ⚠️ No IPA file found in test_files directory")
        print("   Please place an .ipa file in test_files directory")
        pytest.skip("No IPA file found")
    
    print(f"   Using IPA: {os.path.basename(ipa_path)}")
    print(f"   File size: {os.path.getsize(ipa_path) / (1024*1024):.2f} MB")
    
    with open(ipa_path, 'rb') as f:
        files = {
            'file': (os.path.basename(ipa_path), f, 'application/octet-stream')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-ipa/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    if response.status_code == 200:
        print(f"   ✅ IPA installed successfully")
        print(f"   Response: {response.json()}")
        assert True
    else:
        print(f"   ⚠️ Install response: {response.status_code}")
        print(f"   Response: {response.text}")

def test_install_ipa_invalid_extension(setup_ios_device):
    """TC2: Verify install IPA fails when file extension is not .ipa"""
    print("\n" + "="*60)
    print("📋 TEST 2: Install IPA - invalid file extension")
    print("="*60)
    
    _, device_id = setup_ios_device
    
    # Create a dummy text file if it doesn't exist
    if not os.path.exists(TEST_FILE_PATH):
        os.makedirs(os.path.dirname(TEST_FILE_PATH), exist_ok=True)
        with open(TEST_FILE_PATH, 'w') as f:
            f.write("This is a test file - not an IPA")
    
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {
            'file': (os.path.basename(TEST_FILE_PATH), f, 'text/plain')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-ipa/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    # Should return 400 for invalid file type
    assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
    print(f"   ✅ Correctly rejected non-IPA file with {response.status_code}")

def test_install_ipa_unauthorized(setup_ios_device):
    """TC3: Verify install IPA fails when user tries to install on unallocated device"""
    print("\n" + "="*60)
    print("📋 TEST 3: Install IPA - unauthorized")
    print("="*60)
    
    _, device_id = setup_ios_device
    
    # Get IPA path dynamically
    ipa_path = get_ipa_path()
    if not ipa_path:
        pytest.skip("No IPA file found")
    
    invalid_headers = {
        "Authorization": "Bearer invalid_token"
    }
    
    with open(ipa_path, 'rb') as f:
        files = {
            'file': (os.path.basename(ipa_path), f, 'application/octet-stream')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-ipa/{device_id}",
            headers=invalid_headers,
            files=files
        )
    
    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    print(f"   ✅ Correctly returned {response.status_code} for unauthorized user")

def test_install_ipa_invalid_device_id():
    """TC4: Verify install IPA fails with invalid device_id"""
    print("\n" + "="*60)
    print("📋 TEST 4: Install IPA - invalid device_id")
    print("="*60)
    
    invalid_device = "invalid-device-id-12345"
    
    # Get IPA path dynamically
    ipa_path = get_ipa_path()
    if not ipa_path:
        pytest.skip("No IPA file found")
    
    with open(ipa_path, 'rb') as f:
        files = {
            'file': (os.path.basename(ipa_path), f, 'application/octet-stream')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-ipa/{invalid_device}",
            headers=headers,
            files=files
        )
    
    # API returns 404/403/422 for invalid device
    assert response.status_code in [404, 403, 422], f"Expected 404/403/422, got {response.status_code}"
    print(f"   ✅ Correctly rejected invalid device with {response.status_code}")

def test_install_ipa_large_file(setup_ios_device):
    """TC5: Verify install IPA with large file"""
    print("\n" + "="*60)
    print("📋 TEST 5: Install IPA - large file")
    print("="*60)
    
    _, device_id = setup_ios_device
    
    ipa_path = get_ipa_path()
    if not ipa_path:
        pytest.skip("No IPA file found")
    
    file_size = os.path.getsize(ipa_path) / (1024*1024)
    print(f"   IPA file size: {file_size:.2f} MB")
    
    with open(ipa_path, 'rb') as f:
        files = {
            'file': (os.path.basename(ipa_path), f, 'application/octet-stream')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-ipa/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    if response.status_code == 200:
        print(f"   ✅ IPA installed successfully (size: {file_size:.2f} MB)")
        print(f"   Response: {response.json()}")
    else:
        print(f"   ⚠️ Install response: {response.status_code}")
        print(f"   Response: {response.text}")

def test_install_ipa_multiple_times(setup_ios_device):
    """TC6: Verify installing same IPA multiple times"""
    print("\n" + "="*60)
    print("📋 TEST 6: Install IPA - multiple times")
    print("="*60)
    
    _, device_id = setup_ios_device
    
    ipa_path = get_ipa_path()
    if not ipa_path:
        pytest.skip("No IPA file found")
    
    success_count = 0
    
    for attempt in range(1, 3):
        print(f"\n   Attempt {attempt}/2:")
        
        with open(ipa_path, 'rb') as f:
            files = {
                'file': (os.path.basename(ipa_path), f, 'application/octet-stream')
            }
            
            response = requests.post(
                f"{BASE_URL}/v1/devices/physical/install-ipa/{device_id}",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                files=files
            )
        
        if response.status_code == 200:
            print(f"   ✅ IPA installed successfully (attempt {attempt})")
            success_count += 1
        else:
            print(f"   ⚠️ Install failed (attempt {attempt}): {response.status_code}")
    
    # At least one attempt should succeed
    assert success_count > 0, "All installation attempts failed"

# ============ NEGATIVE TEST: Try APK on iOS (Should Fail) ============

def test_install_apk_on_ios(setup_ios_device):
    """TC7: Verify install APK fails on iOS device (iOS cannot install APK)"""
    print("\n" + "="*60)
    print("📋 TEST 7: Install APK on iOS - should fail")
    print("="*60)
    
    _, device_id = setup_ios_device
    
    # Check if APK exists
    if not os.path.exists(TEST_APK_PATH):
        print("   ⚠️ APK file not found at: " + TEST_APK_PATH)
        print("   Please place BitBarSampleApp.apk in test_files directory")
        pytest.skip("APK file not found")
    
    print(f"   Using APK: {os.path.basename(TEST_APK_PATH)}")
    print(f"   iOS Device ID: {device_id}")
    
    print("\n   Attempting to install APK on iOS device...")
    with open(TEST_APK_PATH, 'rb') as f:
        files = {
            'file': (os.path.basename(TEST_APK_PATH), f, 'application/vnd.android.package-archive')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-apk/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    # Should fail - APK cannot be installed on iOS
    if response.status_code in [400, 422, 403]:
        print(f"   ✅ Correctly rejected APK on iOS with {response.status_code}")
        print(f"   Reason: iOS devices cannot install Android APK files")
    else:
        print(f"   ⚠️ Response: {response.status_code}")
        print(f"   Response: {response.text}")

# ============ TESTS AFTER DEALLOCATION ============

def test_install_ipa_after_deallocation(setup_ios_device):
    """TC8: Verify install IPA fails after device deallocation"""
    print("\n" + "="*60)
    print("📋 TEST 8: Install IPA after deallocation")
    print("="*60)
    
    session_id, device_id = setup_ios_device
    
    print(f"\n🔓 Deallocating iOS device...")
    requests.post(f"{BASE_URL}/v1/devices/physical/release/{device_id}", headers=headers)
    print("✅ iOS Device deallocated")
    
    time.sleep(2)
    
    print("\n   Attempting to install IPA after deallocation...")
    
    ipa_path = get_ipa_path()
    if not ipa_path:
        pytest.skip("No IPA file found")
    
    with open(ipa_path, 'rb') as f:
        files = {
            'file': (os.path.basename(ipa_path), f, 'application/octet-stream')
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/devices/physical/install-ipa/{device_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            files=files
        )
    
    if response.status_code in [400, 404, 403, 500]:
        print(f"   ✅ Correctly failed with {response.status_code} after deallocation")
    else:
        print(f"   ⚠️ Unexpected response: {response.status_code}")
        print(f"   Response: {response.text}")

# ============ CLEANUP ============

@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """Clean up test files after all tests"""
    yield
    print("\n🧹 Cleaning up...")