import os
from urllib.parse import parse_qs, unquote

import pytest
import requests

from pathlib import Path
from dotenv import load_dotenv

ENV_FILE = Path(__file__).parent / "test.env"
load_dotenv(ENV_FILE)

API_BASE = os.getenv("FLINT_API_BASE")
TOKEN = os.getenv("TOKEN")


def get_available_android_device():

    response = requests.get(
        f"{API_BASE}/v1/devices/physical/list?os=android",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
        },
        timeout=30,
    )

    response.raise_for_status()

    devices = response.json()

    available_devices = [
        device
        for device in devices
        if device["Availability"].lower() == "available"
    ]

    assert available_devices, "No available Android devices"

    return available_devices[0]["device_id"]


def allocate_device():

    device_id = get_available_android_device()

    print(f"\nSelected Device: {device_id}")

    response = requests.get(
        f"{API_BASE}/v1/devices/physical/get/{device_id}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
        },
        timeout=60,
    )

    response.raise_for_status()

    print("\nAllocation Response:")
    print(response.json())

    return response.json()


def release_device(device_id):

    response = requests.post(
        f"{API_BASE}/v1/devices/physical/release/{device_id}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
        },
        timeout=30,
    )

    print(f"\nReleasing Device: {device_id}")

    response.raise_for_status()


def extract_ws_url(streaming_url):

    fragment = streaming_url.split("#!", 1)[1]

    params = parse_qs(fragment)

    return unquote(params["ws"][0])


@pytest.fixture(scope="session")
def session_data():

    session = allocate_device()

    yield session

    try:
        device_id = session["device_details"]["id"]
        release_device(device_id)
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            print("Device already released")
        else:
            raise


@pytest.fixture(scope="session")
def ws_url(session_data):

    return extract_ws_url(
        session_data["streaming_url"]
    )


@pytest.fixture(scope="session")
def release_device_fn(session_data):

    def _release():
        device_id = session_data["device_details"]["id"]
        release_device(device_id)

    return _release