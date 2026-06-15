import pytest
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(ENV_FILE)

# Configuration
BASE_URL = os.getenv("FLINT_API_BASE", "https://staging.api.flintlab.io")
AUTH_TOKEN = os.getenv("FLINT_API_TOKEN")
WAIT_TIME = int(os.getenv("WAIT_TIME_FOR_LOGS", "20"))

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

@pytest.fixture(scope="module")
def setup_emulator():
    """Setup: Get and allocate emulator"""
    # Get first emulator
    response = requests.get(f"{BASE_URL}/v1/devices/emulator/list", headers=headers)
    if response.status_code != 200:
        pytest.fail(f"Failed to get emulator list: {response.status_code}")
    
    emulators = response.json()
    if not emulators:
        pytest.fail("No emulators available")
    
    recipe_uuid = emulators[0].get("recipe_uuid")
    print(f"✅ Got emulator: {emulators[0].get('name', 'N/A')}")
    
    # Allocate emulator
    response = requests.post(f"{BASE_URL}/v1/devices/emulator/allocate-emulator?recipe_uuid={recipe_uuid}", headers=headers)
    if response.status_code != 200:
        pytest.fail(f"Allocation failed: {response.status_code}")
    
    data = response.json()
    session_id = data.get('session_id')
    device_id = data.get('device_details', {}).get('device_id')
    
    print(f"✅ Emulator allocated - Session ID: {session_id}")
    
    yield session_id, device_id
    
    # Teardown: Stop session
    print(f"\n🛑 Stopping emulator session...")
    requests.post(f"{BASE_URL}/v1/devices/emulator/device/{device_id}/stop/session", headers=headers)

def test_positive_allocate_and_download(setup_emulator):
    """TEST 1: Valid allocation and download"""
    print("\n" + "="*60)
    print("📋 TEST 1: Valid allocation and download")
    print("="*60)
    
    session_id, device_id = setup_emulator
    
    time.sleep(WAIT_TIME)
    
    # Download logs
    response = requests.get(f"{BASE_URL}/v1/devices/emulator/logs/download/{session_id}", headers=headers)
    
    assert response.status_code == 200, f"Download failed: {response.status_code}"
    
    # Save logs to file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"emulator_logs_{session_id}_{timestamp}.log"
    with open(filename, 'wb') as f:
        f.write(response.content)
    
    file_size = len(response.content)
    print(f"✅ Logs downloaded: {filename} ({file_size} bytes)")
    assert file_size > 0, "Log file is empty"

def test_negative_invalid_session_id():
    """TEST 2: Invalid Session ID (Should fail)"""
    print("\n" + "="*60)
    print("📋 TEST 2: Invalid Session ID")
    print("="*60)
    
    invalid_session_id = "invalid-session-id-12345"
    
    response = requests.get(f"{BASE_URL}/v1/devices/emulator/logs/download/{invalid_session_id}", headers=headers)
    
    assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"

def test_download_after_deallocation(setup_emulator):
    """TEST 3: Download logs after deallocation (Should still work)"""
    print("\n" + "="*60)
    print("📋 TEST 3: Download logs after deallocation")
    print("="*60)
    
    session_id, device_id = setup_emulator
    
    # Stop session first
    requests.post(f"{BASE_URL}/v1/devices/emulator/device/{device_id}/stop/session", headers=headers)
    
    time.sleep(3)
    
    # Try to download after deallocation
    response = requests.get(f"{BASE_URL}/v1/devices/emulator/logs/download/{session_id}", headers=headers)
    
    # Logs should still be accessible after deallocation
    assert response.status_code == 200, f"Expected 200 after deallocation, got {response.status_code}"
    
    if response.status_code == 200:
        file_size = len(response.content)
        print(f"✅ Logs still accessible after deallocation ({file_size} bytes)")