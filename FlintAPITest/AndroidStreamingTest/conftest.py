import os
from urllib.parse import parse_qs, unquote

import pytest
import requests

from pathlib import Path
from dotenv import load_dotenv

ENV_FILE = Path(__file__).parent / "test.env"
load_dotenv(ENV_FILE)


API_BASE = os.getenv("FLINT_API_BASE")
DEVICE_ID = os.getenv("DEVICE_ID")
TOKEN = os.getenv("TOKEN")


def get_session():

    response = requests.get(
        f"{API_BASE}/v1/devices/physical/get/{DEVICE_ID}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def extract_ws_url(streaming_url):

    fragment = streaming_url.split("#!", 1)[1]

    params = parse_qs(fragment)

    return unquote(params["ws"][0])

def release_device():

    response = requests.post(
        f"{API_BASE}/v1/devices/physical/release/{DEVICE_ID}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()

@pytest.fixture(scope="session")
def release_device_fn():
    return release_device

@pytest.fixture(scope="session")
def session_data():

    return get_session()


@pytest.fixture(scope="session")
def ws_url(session_data):

    return extract_ws_url(
        session_data["streaming_url"]
    )