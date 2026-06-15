import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(ENV_FILE)

# Configuration from .env
BASE_URL = os.getenv("FLINT_API_BASE", "https://staging.api.flintlab.io")
AUTH_TOKEN = os.getenv("FLINT_API_TOKEN")
WAIT_TIME = int(os.getenv("WAIT_TIME_FOR_LOGS", "20"))

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def download_emulator_logs(session_id):
    """Download emulator logs for a session"""
    print(f"\n📥 Downloading logs for session: {session_id}")
    
    response = requests.get(
        f"{BASE_URL}/v1/devices/emulator/logs/download/{session_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Download failed: {response.status_code}")
        if response.status_code == 401:
            print(f"   Unauthorized - Invalid token")
        elif response.status_code == 404:
            print(f"   Not Found - Invalid session ID")
        return None, response.status_code
    
    # Save logs to file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"emulator_logs_{session_id}_{timestamp}.log"
    with open(filename, 'wb') as f:
        f.write(response.content)
    
    file_size = len(response.content)
    print(f"✅ Logs downloaded: {filename} ({file_size} bytes)")
    return filename, response.status_code

def test_positive_allocate_and_download():
    """Positive Test: Valid allocation and download"""
    print("\n" + "="*60)
    print("✅ POSITIVE TEST: Valid allocation and download")
    print("="*60)
    
    # Step 1: Get first emulator
    print("\n📋 Getting first available emulator...")
    response = requests.get(
        f"{BASE_URL}/v1/devices/emulator/list",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get emulator list: {response.status_code}")
        return False, None, None
    
    emulators = response.json()
    if not emulators:
        print("❌ No emulators available")
        return False, None, None
    
    emulator = emulators[0]
    recipe_uuid = emulator.get("recipe_uuid")
    emulator_name = emulator.get("name", "N/A")
    print(f"✅ Got emulator: {emulator_name}")
    
    # Step 2: Allocate emulator
    print(f"\n📱 Allocating emulator...")
    response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/allocate-emulator?recipe_uuid={recipe_uuid}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Allocation failed: {response.status_code}")
        return False, None, None
    
    data = response.json()
    session_id = data.get('session_id')
    device_id = data.get('device_details', {}).get('device_id')
    
    print(f"✅ Emulator allocated")
    print(f"   Session ID: {session_id}")
    print(f"   Device ID: {device_id}")
    
    # Step 3: Wait for logs
    print(f"\n⏳ Waiting {WAIT_TIME} seconds for logs to be generated...")
    time.sleep(WAIT_TIME)
    
    # Step 4: Download logs
    filename, status = download_emulator_logs(session_id)
    if not filename:
        return False, session_id, device_id
    
    return True, session_id, device_id

def test_negative_invalid_session_id():
    """Negative Test 1: Download logs with invalid session ID"""
    print("\n" + "="*60)
    print("❌ NEGATIVE TEST 1: Invalid Session ID")
    print("="*60)
    
    invalid_session_id = "invalid-session-id-12345"
    
    print(f"\n   Testing with invalid session_id: '{invalid_session_id}'")
    print(f"   (No allocation performed - directly testing invalid ID)")
    
    response = requests.get(
        f"{BASE_URL}/v1/devices/emulator/logs/download/{invalid_session_id}",
        headers=headers
    )
    
    print(f"\n   Response status code: {response.status_code}")
    
    if response.status_code == 404:
        print(f"   ✅ PASSED - Correctly returned 404 (Not Found)")
        return True
    elif response.status_code == 400:
        print(f"   ✅ PASSED - Correctly returned 400 (Bad Request)")
        return True
    elif response.status_code == 401:
        print(f"   ✅ PASSED - Correctly returned 401 (Unauthorized)")
        return True
    else:
        print(f"   ❌ FAILED - Expected 400/401/404, got {response.status_code}")
        return False

def test_negative_download_after_deallocation(session_id, device_id):
    """Negative Test 2: Try to download logs after session is stopped"""
    print("\n" + "="*60)
    print(" Download logs after session deallocation")
    print("="*60)
    
    if not session_id or not device_id:
        print("   ⚠️ Skipping - No valid session from positive test")
        return False
    
    print(f"\n   Original Session ID: {session_id}")
    print(f"   Original Device ID: {device_id}")
    
    # Step 1: Stop the session
    print(f"\n🛑 Stopping emulator session...")
    response = requests.post(
        f"{BASE_URL}/v1/devices/emulator/device/{device_id}/stop/session",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Stop failed: {response.status_code}")
        return False
    
    print(f"✅ Session stopped successfully")
    
    # Step 2: Wait a moment
    print("\n⏳ Waiting 3 seconds after session stop...")
    time.sleep(3)
    
    # Step 3: Try to download logs
    print(f"\n📥 Attempting to download logs with same session ID after deallocation...")
    response = requests.get(
        f"{BASE_URL}/v1/devices/emulator/logs/download/{session_id}",
        headers=headers
    )
    
    print(f"\n   Response status code: {response.status_code}")
    
    if response.status_code == 404:
        print(f"   ❌ FAILED - Session is not accessible after deallocation")
        return False
    elif response.status_code == 400:
        print(f"   ❌ FAILED - Session is not accessible after deallocation")
        return False
    elif response.status_code == 410:
        print(f"   ❌ FAILED - Session is not accessible after deallocation")
        return False
    elif response.status_code == 200:
        print(f"   ✅ PASSED - Correctly returned")
        return True
    else:
        print(f"   ⚠️ Unexpected response: {response.status_code}")
        return False

def run_tests():
    print("="*60)
    print("🚀 EMULATOR LOG AUTOMATION")
    print(f"   API Base URL: {BASE_URL}")
    print(f"   Wait Time: {WAIT_TIME} seconds")
    print("="*60)
    
    results = []
    session_id = None
    device_id = None
    
    # Positive test
    print("\n🟢 RUNNING POSITIVE TEST")
    try:
        result, session_id, device_id = test_positive_allocate_and_download()
        results.append(("POSITIVE: Allocate & Download", "PASSED" if result else "FAILED"))
    except Exception as e:
        results.append(("POSITIVE: Allocate & Download", f"FAILED: {e}"))
    
    # Negative test 1: Invalid session ID
    print("\n🔴 RUNNING NEGATIVE TEST 1: Invalid Session ID")
    try:
        result = test_negative_invalid_session_id()
        results.append(("NEGATIVE: Invalid Session ID", "PASSED" if result else "FAILED"))
    except Exception as e:
        results.append(("NEGATIVE: Invalid Session ID", f"FAILED: {e}"))
    
    # Negative test 2: Download after deallocation
    print("\n🔴 RUNNING NEGATIVE TEST 2: Download After Deallocation")
    try:
        result = test_negative_download_after_deallocation(session_id, device_id)
        results.append(("NEGATIVE: Download After Deallocation", "PASSED" if result else "FAILED"))
    except Exception as e:
        results.append(("NEGATIVE: Download After Deallocation", f"FAILED: {e}"))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test, result in results:
        if "PASSED" in result:
            print(f"   ✅ {test}: {result}")
        else:
            print(f"   ❌ {test}: {result}")
    
    passed = sum(1 for _, r in results if r == "PASSED")
    total = len(results)
    print(f"\n   📈 {passed}/{total} tests passed")
    print("="*60)

if __name__ == "__main__":
    run_tests()