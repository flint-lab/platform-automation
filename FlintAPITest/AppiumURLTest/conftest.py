import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "test.env")

logger = logging.getLogger("flint.appium_url")


class Config:
    BASE_URL: str = os.environ.get("FLINT_BASE_URL", "").rstrip("/")
    AUTH_TOKEN: str = os.environ.get("FLINT_AUTH_TOKEN", "")
    # Second identity — needed only for tenant-isolation tests (TC-006, TC-014).
    AUTH_TOKEN_B: str = os.environ.get("FLINT_AUTH_TOKEN_B", "")

    # What to allocate. Emulator uses a recipe uuid (auto-discovered from /list if
    # blank); physical uses a device id.
    SURFACE: str = os.environ.get("FLINT_SURFACE", "emulator")
    RECIPE_UUID: str = os.environ.get("FLINT_RECIPE_UUID", "")
    PHYSICAL_DEVICE_ID: str = os.environ.get("FLINT_PHYSICAL_DEVICE_ID", "")

    # Thresholds (no test hardcodes these).
    CONNECT_WINDOW_S: float = float(os.environ.get("FLINT_CONNECT_WINDOW_S", "60"))
    IDLE_GRACE_S: float = float(os.environ.get("FLINT_IDLE_GRACE_S", "300"))
    GC_INTERVAL_S: float = float(os.environ.get("FLINT_GC_INTERVAL_S", "120"))
    POOL_SIZE: int = int(os.environ.get("FLINT_POOL_SIZE", "5"))
    CONCURRENCY_CAP: int = int(os.environ.get("FLINT_CONCURRENCY_CAP", "3"))
    RATE_LIMIT_PER_SECOND: int = int(os.environ.get("FLINT_RATE_LIMIT_PER_SECOND", "50"))

    @classmethod
    def validate(cls) -> None:
        missing = [k for k in ("BASE_URL", "AUTH_TOKEN") if not getattr(cls, k)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Fill in the values in test.env."
            )


Config.validate()


# --------------------------------------------------------------------------- #
# --env gate: destructive tests break the server/host on purpose and must NEVER
# run against preprod/production. They run only with --env staging.
# --------------------------------------------------------------------------- #
def pytest_addoption(parser):
    parser.addoption(
        "--env", action="store", default="preprod",
        choices=("preprod", "staging", "production"),
        help="Target env. Destructive tests run ONLY with --env staging.",
    )


def pytest_collection_modifyitems(config, items):
    env = config.getoption("--env")
    for item in items:
        if "destructive" in item.keywords and env != "staging":
            reason = (
                "destructive: HARD-BLOCKED on production"
                if env == "production"
                else f"destructive: runs only with --env staging (current: {env})"
            )
            item.add_marker(pytest.mark.skip(reason=reason))


# --------------------------------------------------------------------------- #
# HTTP clients
# --------------------------------------------------------------------------- #
def _client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url=Config.BASE_URL,
        headers={"Authorization": token},
        timeout=httpx.Timeout(60.0, connect=10.0),
    )


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    with _client(Config.AUTH_TOKEN) as c:
        yield c


@pytest.fixture(scope="session")
def client_b() -> httpx.Client:
    if not Config.AUTH_TOKEN_B:
        pytest.skip("FLINT_AUTH_TOKEN_B not set — needed for tenant-isolation tests")
    with _client(Config.AUTH_TOKEN_B) as c:
        yield c


@pytest.fixture(scope="session")
def recipe_uuid(client: httpx.Client) -> str:
    """Emulator recipe to allocate — from env or the first one /list returns."""
    if Config.RECIPE_UUID:
        return Config.RECIPE_UUID
    resp = client.get("/v1/devices/emulator/list", timeout=30.0)
    resp.raise_for_status()
    recipes = resp.json()
    if not recipes:
        pytest.skip("No emulator recipes available in this environment")
    return recipes[0]["recipe_uuid"]


# --------------------------------------------------------------------------- #
# Allocation helpers — normalize both surfaces to one shape.
# Field names (discovered in the services):
#   emulator -> appium_configuration.{appium_url, token, device_id, appium_url_expires_at}
#   physical -> appium_url + appium_inspector_configuration.{remote_host, ...}
# --------------------------------------------------------------------------- #
def allocate(client: httpx.Client, surface: str, ref: str) -> dict:
    """Allocate a device; return {appium_url, token, device_id, expires_at, raw}."""
    if surface == "emulator":
        with client.stream(
            "POST", "/v1/devices/emulator/allocate-emulator",
            params={"recipe_uuid": ref}, timeout=180.0,
        ) as resp:
            resp.raise_for_status()
            last = b""
            for chunk in resp.iter_bytes():
                if chunk.strip():
                    last = chunk.strip()
        data = json.loads(last)
        if "session_id" not in data:
            raise RuntimeError(f"Allocation failed: {data.get('detail', data)}")
        cfg = data.get("appium_configuration", {})
        return {
            "surface": surface,
            "appium_url": cfg.get("appium_url", ""),
            "token": cfg.get("token"),
            "device_id": data["device_details"]["device_id"],
            "expires_at": cfg.get("appium_url_expires_at"),
            "session_id": data.get("session_id"),
            "raw": data,
        }

    resp = client.get(f"/v1/devices/physical/get/{ref}", timeout=180.0)
    resp.raise_for_status()
    data = resp.json()
    return {
        "surface": surface,
        "appium_url": data.get("appium_url", ""),
        "token": None,
        "device_id": (data.get("device_details") or {}).get("device_id", ref),
        "expires_at": data.get("session_ends_at"),
        "session_id": data.get("session_id"),
        "raw": data,
    }


def release(client: httpx.Client, alloc: dict) -> None:
    """Best-effort release/stop of an allocation."""
    surface, device_id = alloc["surface"], alloc["device_id"]
    try:
        if surface == "emulator":
            client.post(f"/v1/devices/emulator/device/{device_id}/stop/session", timeout=30.0)
        else:
            client.post(f"/v1/devices/physical/release/{device_id}", timeout=30.0)
    except Exception as exc:
        logger.warning("cleanup release failed for %s: %s", device_id, exc)


def _ref_for(surface: str, recipe_uuid: str) -> str:
    if surface == "physical":
        if not Config.PHYSICAL_DEVICE_ID:
            pytest.skip("FLINT_PHYSICAL_DEVICE_ID not set — physical surface unavailable")
        return Config.PHYSICAL_DEVICE_ID
    return recipe_uuid


@pytest.fixture
def appium_url(client: httpx.Client, recipe_uuid: str) -> dict:
    """Fetch a real, fresh Appium URL; always release on teardown."""
    alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
    logger.info("allocated %s | device=%s url=%s", Config.SURFACE, alloc["device_id"], alloc["appium_url"])
    yield alloc
    release(client, alloc)


# --------------------------------------------------------------------------- #
# Appium connect helper + capability builder (OS chosen purely via caps).
# --------------------------------------------------------------------------- #
def caps_for(alloc: dict, os_override: str | None = None) -> tuple[str, dict]:
    details = (alloc.get("raw") or {}).get("device_details") or {}
    os_name = (os_override or details.get("os") or "android").lower()
    os_name = "ios" if "ios" in os_name else "android"
    if os_name == "android":
        caps = {
            "platformName": "Android",
            "appium:automationName": "UiAutomator2",
            "appium:newCommandTimeout": 120,
        }
    else:
        caps = {"platformName": "iOS", "appium:automationName": "XCUITest", "appium:newCommandTimeout": 120}
    udid = details.get("udid") or details.get("real_device_id") or alloc.get("device_id")
    if udid:
        caps["appium:udid"] = udid
    if details.get("os_version"):
        caps["appium:platformVersion"] = str(details["os_version"])
    return os_name, caps


def connect_driver(appium_url: str, os_name: str, caps: dict):
    """Create an Appium session against the URL. Caller must driver.quit()."""
    from appium import webdriver
    from appium.options.android import UiAutomator2Options
    from appium.options.ios import XCUITestOptions

    options = UiAutomator2Options() if os_name == "android" else XCUITestOptions()
    options.load_capabilities(caps)
    return webdriver.Remote(command_executor=appium_url, options=options)


# --------------------------------------------------------------------------- #
# URL-mutation helpers — derive controlled negatives from a real URL.
# URL shape: …/connect/<token>/wd/hub
# --------------------------------------------------------------------------- #
_CONNECT_RE = re.compile(r"(/connect/)([^/]+)(/wd/hub.*)")


def tamper_token(appium_url: str) -> str:
    m = _CONNECT_RE.search(appium_url)
    if not m:
        return appium_url[:-1] + ("0" if appium_url[-1] != "0" else "1")
    tok = m.group(2)
    flipped = "".join("0" if c != "0" else "1" for c in tok[:8]) + tok[8:]
    return appium_url[: m.start(2)] + flipped + appium_url[m.end(2):]


def unreachable_host(appium_url: str) -> str:
    p = urlparse(appium_url)
    return urlunparse(p._replace(netloc="127.0.0.1:1"))


def probe_session(appium_url: str, timeout: float = 20.0) -> httpx.Response:
    """Raw POST /session against a URL — no Appium client needed (for negatives)."""
    body = {"capabilities": {"alwaysMatch": {"platformName": "Android"}}}
    return httpx.post(f"{appium_url.rstrip('/')}/session", json=body, timeout=timeout, verify=False)
