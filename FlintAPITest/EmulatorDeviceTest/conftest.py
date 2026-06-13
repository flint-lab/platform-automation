import json
import logging
import os
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "test.env")

logger = logging.getLogger("flint.emulator")


class Config:
    BASE_URL: str = os.environ.get("FLINT_BASE_URL", "").rstrip("/")
    AUTH_TOKEN: str = os.environ.get("FLINT_AUTH_TOKEN", "")
    APK_PATH: str | None = os.environ.get("FLINT_TEST_APK_PATH")
    UPLOAD_FILE_PATH: str | None = os.environ.get("FLINT_TEST_UPLOAD_FILE_PATH")

    @classmethod
    def validate(cls) -> None:
        missing = [k for k in ("BASE_URL", "AUTH_TOKEN") if not getattr(cls, k)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Fill in the values in test.env."
            )


Config.validate()


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    with httpx.Client(
        base_url=Config.BASE_URL,
        headers={"Authorization": Config.AUTH_TOKEN},
        timeout=httpx.Timeout(60.0, connect=10.0),
    ) as c:
        yield c


@pytest.fixture(scope="session")
def recipe_uuid(client: httpx.Client) -> str:
    """Fetch the first available emulator recipe UUID from the live environment."""
    logger.info("Fetching available emulator recipes from %s ...", Config.BASE_URL)
    response = client.get("/v1/devices/emulator/list", timeout=30.0)
    response.raise_for_status()
    recipes = response.json()
    if not recipes:
        pytest.skip("No emulator recipes available in this environment")
    uuid = recipes[0]["recipe_uuid"]
    name = recipes[0].get("name", "unknown")
    logger.info("Using recipe: %s (%s)", name, uuid)
    return uuid


def allocate_emulator(client: httpx.Client, recipe_uuid: str) -> dict:
    """Allocate an emulator and return the parsed session response.

    The allocate endpoint streams keep-alive newlines while the container
    starts, then emits the final JSON payload.
    """
    logger.info("Allocating emulator (recipe=%s) — waiting for container to start ...", recipe_uuid)
    with client.stream(
        "POST",
        "/v1/devices/emulator/allocate-emulator",
        params={"recipe_uuid": recipe_uuid},
        timeout=180.0,
    ) as response:
        response.raise_for_status()
        last_data = b""
        for chunk in response.iter_bytes():
            stripped = chunk.strip()
            if stripped:
                last_data = stripped

    data = json.loads(last_data)
    if "session_id" not in data:
        raise RuntimeError(f"Allocation failed: {data.get('detail', data)}")

    logger.info(
        "Emulator allocated | device_id=%s  session_id=%s",
        data["device_details"]["device_id"],
        data["session_id"],
    )
    return data


def stop_emulator(client: httpx.Client, device_id: str) -> None:
    """Stop an emulator session. Silently ignores errors (best-effort cleanup)."""
    logger.info("Stopping emulator | device_id=%s", device_id)
    try:
        client.post(
            f"/v1/devices/emulator/device/{device_id}/stop/session",
            timeout=30.0,
        )
        logger.info("Emulator stopped | device_id=%s", device_id)
    except Exception as exc:
        logger.warning("Cleanup stop failed for device_id=%s: %s", device_id, exc)


@pytest.fixture
def allocated_emulator(client: httpx.Client, recipe_uuid: str) -> dict:
    """Allocate an emulator before the test and guarantee it is stopped after."""
    session = allocate_emulator(client, recipe_uuid)
    yield session
    if not session.get("_stopped"):
        stop_emulator(client, session["device_details"]["device_id"])
