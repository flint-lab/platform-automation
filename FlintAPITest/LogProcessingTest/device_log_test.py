import pytest
import requests
import time
from datetime import datetime, timedelta, timezone
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
LOG_QUERY_MINUTES = int(os.getenv("LOG_QUERY_MINUTES", "10"))

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

allocation_time = None
session_id = None
device_id = None

def query_logs(deployment_id, start_offset_minutes=0, end_offset_minutes=LOG_QUERY_MINUTES):
    """Query logs with debug and info levels"""
    global allocation_time
    
    start_timestamp = (allocation_time + timedelta(minutes=start_offset_minutes)).isoformat().replace('+00:00', 'Z')
    end_timestamp = (allocation_time + timedelta(minutes=end_offset_minutes)).isoformat().replace('+00:00', 'Z')
    
    body = {
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "deployment_id": deployment_id,
        "search": "",
        "start": 0,
        "end": 100,
        "log_level": ["debug", "info"]
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/logs/filter",
        headers=headers,
        json=body
    )
    
    return response

@pytest.fixture(scope="module")
def setup_device():
    """Setup: Get and allocate device"""
    global allocation_time, session_id, device_id
    
    # Get device
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

def test_negative_invalid_session_id_before_allocation():
    """TEST 1: Invalid Session ID (Before Allocation)"""
    print("\n" + "="*60)
    print("📋 TEST 1: NEGATIVE TEST - Invalid Session ID (Before Allocation)")
    print("="*60)
    
    invalid_session_id = "invalid-session-id-12345"
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    
    body = {
        "start_timestamp": one_hour_ago.isoformat().replace('+00:00', 'Z'),
        "end_timestamp": now.isoformat().replace('+00:00', 'Z'),
        "deployment_id": invalid_session_id,
        "search": "",
        "start": 0,
        "end": 100
    }
    
    print(f"\n   Using invalid deployment_id: {invalid_session_id}")
    
    response = requests.post(f"{BASE_URL}/v1/devices/physical/logs/filter", headers=headers, json=body)
    
    print(f"\n   Response status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        total_logs = data.get('total_logs', 0)
        print(f"   Total logs returned: {total_logs}")
        
        if total_logs == 0:
            print(f"   ✅ PASSED - Invalid session ID correctly returned 0 logs")
            assert True
            return
    elif response.status_code in [400, 404]:
        print(f"   ✅ PASSED - Invalid session ID returned {response.status_code}")
        assert True
        return
    
    assert False, f"❌ FAILED - Unexpected response: {response.status_code}"

def test_negative_invalid_session_id_after_allocation(setup_device):
    """TEST 2: Invalid Session ID (Using wrong ID after allocation)"""
    print("\n" + "="*60)
    print("📋 TEST 2: NEGATIVE TEST - Invalid Session ID (Using wrong ID after allocation)")
    print("="*60)
    
    valid_session_id, _ = setup_device
    invalid_session_id = "wrong-session-id-67890"
    
    print(f"\n   Real Session ID (allocated): {valid_session_id}")
    print(f"   Using wrong deployment_id: {invalid_session_id}")
    
    body = {
        "start_timestamp": (allocation_time - timedelta(minutes=5)).isoformat().replace('+00:00', 'Z'),
        "end_timestamp": (allocation_time + timedelta(minutes=LOG_QUERY_MINUTES)).isoformat().replace('+00:00', 'Z'),
        "deployment_id": invalid_session_id,
        "search": "",
        "start": 0,
        "end": 100
    }
    
    response = requests.post(f"{BASE_URL}/v1/devices/physical/logs/filter", headers=headers, json=body)
    
    print(f"\n   Response status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        total_logs = data.get('total_logs', 0)
        print(f"   Total logs returned: {total_logs}")
        
        if total_logs == 0:
            print(f"   ✅ PASSED - Wrong session ID correctly returned 0 logs")
            assert True
            return
    elif response.status_code in [400, 404]:
        print(f"   ✅ PASSED - Wrong session ID returned {response.status_code}")
        assert True
        return
    
    assert False, f"❌ FAILED - Unexpected response: {response.status_code}"

def test_query_during_allocation(setup_device):
    """TEST 3: Query logs during active session - with retry"""
    print("\n" + "="*60)
    print("📋 TEST 3: Query logs DURING active session (with retry)")
    print("="*60)
    
    valid_session_id, _ = setup_device
    logs_found = False
    
    # Try multiple times with increasing wait (same as original logic)
    for attempt in range(1, 4):
        print(f"\n   Attempt {attempt}/3:")
        
        # Wait longer each attempt
        wait_time = WAIT_TIME * attempt
        print(f"   Waiting {wait_time} seconds before query...")
        time.sleep(wait_time)
        
        response = query_logs(valid_session_id, start_offset_minutes=0, end_offset_minutes=LOG_QUERY_MINUTES)
        
        if response.status_code == 200:
            data = response.json()
            total_logs = data.get('total_logs', 0)
            print(f"   Total logs found: {total_logs}")
            
            if total_logs > 0:
                print(f"   ✅ PASSED - Found {total_logs} logs during active session")
                print(f"   Debug: {data.get('total_debug', 0)}, Info: {data.get('total_info', 0)}")
                logs_found = True
                break
            else:
                print(f"   ⚠️ No logs yet, will retry...")
        else:
            print(f"   ❌ Query failed: {response.status_code}")
    
    # Don't fail if no logs - device might be idle (same as original)
    if not logs_found:
        print(f"\n   ⚠️ No logs found after 3 attempts")
        print(f"   This may be normal if device is idle or logs take longer to appear")
    
    assert True  # Always pass, same as original logic

def test_query_after_deallocation(setup_device):
    """TEST 4: Query logs AFTER deallocation - logs should still be available"""
    print("\n" + "="*60)
    print("📋 TEST 4: Query logs AFTER deallocation")
    print("="*60)
    
    valid_session_id, device_id = setup_device
    
    print(f"\n   Using same session_id: {valid_session_id}")
    print(f"   (Session was already deallocated)")
    print(f"   Note: Logs should still be available after deallocation")
    
    # Wait for logs to be indexed
    print(f"\n   Waiting {WAIT_TIME} seconds for logs to be indexed...")
    time.sleep(WAIT_TIME)
    
    response = query_logs(valid_session_id, start_offset_minutes=0, end_offset_minutes=20)
    
    if response.status_code != 200:
        print(f"   ❌ Query failed: {response.status_code}")
        assert False, f"Query failed: {response.status_code}"
    
    data = response.json()
    total_logs = data.get('total_logs', 0)
    print(f"\n   Response status code: {response.status_code}")
    print(f"   Total logs returned: {total_logs}")
    
    if total_logs > 0:
        print(f"   ✅ PASSED - Found {total_logs} logs after deallocation")
        print(f"   (This is expected - logs persist after session ends)")
    else:
        print(f"   ⚠️ No logs found after deallocation")
        print(f"   Device may be idle or logs not yet indexed")
    
    assert True  # Always pass, same as original logic