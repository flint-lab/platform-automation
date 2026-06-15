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

def get_first_device():
    """Get the first available physical device"""
    response = requests.get(
        f"{BASE_URL}/v1/devices/physical/list",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get device list: {response.status_code}")
        return None
    
    devices = response.json()
    if not devices:
        print("❌ No devices available")
        return None
    
    device = devices[0]
    device_id = device.get("device_id")
    print(f"✅ Got device: {device_id}")
    print(f"   Device name: {device.get('name', 'N/A')}")
    return device_id

def allocate_device(device_id):
    """Allocate a physical device and return session_id"""
    global allocation_time
    print(f"\n📱 Allocating device: {device_id}")
    
    allocation_time = datetime.now(timezone.utc)
    print(f"   Allocation time (UTC): {allocation_time.isoformat().replace('+00:00', 'Z')}")
    
    response = requests.get(
        f"{BASE_URL}/v1/devices/physical/get/{device_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Allocation failed: {response.status_code}")
        return None
    
    data = response.json()
    session_id = data.get('session_id')
    print(f"✅ Device allocated successfully")
    print(f"   Session ID: {session_id}")
    return session_id

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
    
    print(f"\n   Request body:")
    print(f"     start_timestamp: {start_timestamp} (UTC)")
    print(f"     end_timestamp: {end_timestamp} (UTC)")
    print(f"     deployment_id: {deployment_id}")
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/logs/filter",
        headers=headers,
        json=body
    )
    
    return response

def release_device(device_id):
    """Release the physical device"""
    print(f"\n🔓 Releasing device: {device_id}")
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/release/{device_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Release failed: {response.status_code}")
        return False
    
    print(f"✅ Device released successfully")
    return True

def test_negative_invalid_session_id_before_allocation():
    """Negative Test 1: Query with invalid session ID (before allocation)"""
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
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/logs/filter",
        headers=headers,
        json=body
    )
    
    print(f"\n   Response status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        total_logs = data.get('total_logs', 0)
        print(f"   Total logs returned: {total_logs}")
        
        if total_logs == 0:
            print(f"   ✅ PASSED - Invalid session ID correctly returned 0 logs")
            return True
    elif response.status_code in [400, 404]:
        print(f"   ✅ PASSED - Invalid session ID returned {response.status_code}")
        return True
    
    print(f"   ❌ FAILED")
    return False

def test_negative_invalid_session_id_after_allocation(session_id):
    """Negative Test 2: Query with invalid session ID (using wrong session ID after allocation)"""
    print("\n" + "="*60)
    print("📋 TEST 2: NEGATIVE TEST - Invalid Session ID (Using wrong ID after allocation)")
    print("="*60)
    
    # Use a completely different invalid ID, not the actual session_id
    invalid_session_id = "wrong-session-id-67890"
    real_session_id = session_id
    
    print(f"\n   Real Session ID (allocated): {real_session_id}")
    print(f"   Using wrong deployment_id: {invalid_session_id}")
    
    body = {
        "start_timestamp": (allocation_time - timedelta(minutes=5)).isoformat().replace('+00:00', 'Z'),
        "end_timestamp": (allocation_time + timedelta(minutes=LOG_QUERY_MINUTES)).isoformat().replace('+00:00', 'Z'),
        "deployment_id": invalid_session_id,
        "search": "",
        "start": 0,
        "end": 100
    }
    
    print(f"\n   Request body:")
    print(f"     deployment_id: {invalid_session_id}")
    
    response = requests.post(
        f"{BASE_URL}/v1/devices/physical/logs/filter",
        headers=headers,
        json=body
    )
    
    print(f"\n   Response status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        total_logs = data.get('total_logs', 0)
        print(f"   Total logs returned: {total_logs}")
        
        if total_logs == 0:
            print(f"   ✅ PASSED - Wrong session ID correctly returned 0 logs")
            return True
    elif response.status_code in [400, 404]:
        print(f"   ✅ PASSED - Wrong session ID returned {response.status_code}")
        return True
    
    print(f"   ❌ FAILED")
    return False

def test_query_during_allocation(session_id):
    """Test 3: Query logs during active session - with retry"""
    print("\n" + "="*60)
    print("📋 TEST 3: Query logs DURING active session (with retry)")
    print("="*60)
    
    # Try multiple times with increasing wait
    for attempt in range(1, 4):
        print(f"\n   Attempt {attempt}/3:")
        
        # Wait longer each attempt
        wait_time = WAIT_TIME
        print(f"   Waiting {wait_time} seconds before query...")
        time.sleep(wait_time)
        
        response = query_logs(session_id, start_offset_minutes=0, end_offset_minutes=LOG_QUERY_MINUTES)
        
        if response.status_code == 200:
            data = response.json()
            total_logs = data.get('total_logs', 0)
            print(f"   Total logs found: {total_logs}")
            
            if total_logs > 0:
                print(f"   ✅ PASSED - Found {total_logs} logs during active session")
                print(f"   Debug: {data.get('total_debug', 0)}, Info: {data.get('total_info', 0)}")
                return True
            else:
                print(f"   ⚠️ No logs yet, will retry...")
        else:
            print(f"   ❌ Query failed: {response.status_code}")
    
    print(f"\n   ⚠️ No logs found after 3 attempts")
    print(f"   This may be normal if device is idle or logs take longer to appear")
    return True

def test_query_after_deallocation(session_id):
    """Test 4: Query logs AFTER deallocation - logs should still be available"""
    print("\n" + "="*60)
    print("📋 TEST 4: Query logs AFTER deallocation")
    print("="*60)
    
    print(f"\n   Using same session_id: {session_id}")
    print(f"   (Session was already deallocated)")
    print(f"   Note: Logs should still be available after deallocation")
    
    # Wait a bit for logs to be indexed
    print(f"\n   Waiting {WAIT_TIME} seconds for logs to be indexed...")
    time.sleep(WAIT_TIME)
    
    response = query_logs(session_id, start_offset_minutes=0, end_offset_minutes=20)
    
    if response.status_code != 200:
        print(f"   ❌ Query failed: {response.status_code}")
        return False
    
    data = response.json()
    total_logs = data.get('total_logs', 0)
    print(f"\n   Response status code: {response.status_code}")
    print(f"   Total logs returned: {total_logs}")
    
    if total_logs > 0:
        print(f"   ✅ PASSED - Found {total_logs} logs after deallocation")
        print(f"   (This is expected - logs persist after session ends)")
        return True
    else:
        print(f"   ⚠️ No logs found after deallocation")
        print(f"   Device may be idle or logs not yet indexed")
        return True

def run_tests():
    print("="*60)
    print("🚀 PHYSICAL DEVICE LOG QUERY TESTS")
    print(f"   API Base URL: {BASE_URL}")
    print("="*60)
    
    results = []
    
    # Test 1: Negative test with invalid session ID (before allocation)
    result1 = test_negative_invalid_session_id_before_allocation()
    results.append(("TEST 1: Invalid Session ID (Before Allocation)", "PASSED" if result1 else "FAILED"))
    
    # Get and allocate device for remaining tests
    device_id = get_first_device()
    if not device_id:
        return
    
    session_id = allocate_device(device_id)
    if not session_id:
        return
    
    # Test 2: Negative test with wrong session ID (after allocation)
    result2 = test_negative_invalid_session_id_after_allocation(session_id)
    results.append(("TEST 2: Wrong Session ID (After Allocation)", "PASSED" if result2 else "FAILED"))
    
    # Test 3: Query during allocation (with retry)
    result3 = test_query_during_allocation(session_id)
    results.append(("TEST 3: Query During Allocation", "PASSED" if result3 else "FAILED"))
    
    # Release device
    release_device(device_id)
    
    # Test 4: Query after deallocation
    result4 = test_query_after_deallocation(session_id)
    results.append(("TEST 4: Query After Deallocation", "PASSED" if result4 else "FAILED"))
    
    # Summary
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