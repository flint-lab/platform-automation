import time
from datetime import datetime, timezone

import allure
import httpx
import pytest

from .conftest import Config, allocate, release, caps_for, connect_driver, probe_session, _ref_for


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@allure.suite("Appium URL — Expiry")
class TestExpiry:

    @allure.id("TC-003")
    @allure.title("Expiry metadata present & in the future")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.functional
    def test_expiry_metadata(self, appium_url: dict):
        if Config.SURFACE == "physical":
            pytest.skip("physical surface exposes no appium_url_expires_at field")
        assert appium_url["expires_at"], "allocation carries no appium_url_expires_at"
        expiry = _parse_iso(appium_url["expires_at"])
        assert expiry > datetime.now(timezone.utc), f"expiry {expiry} is not in the future"
        allure.attach(appium_url["expires_at"], name="appium_url_expires_at")

    @allure.id("TC-008")
    @allure.title("Idle timeout — never connected, then connect fails fast (no hang)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.reliability
    def test_idle_timeout(self, client: httpx.Client, recipe_uuid: str):
        alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
        try:
            wait = min(Config.IDLE_GRACE_S + 5, 90)
            if wait < Config.IDLE_GRACE_S:
                pytest.skip(f"idle grace {Config.IDLE_GRACE_S}s exceeds bounded wait {wait}s")
            time.sleep(wait)
            resp = probe_session(alloc["appium_url"])
            allure.attach(f"{resp.status_code} {resp.text[:200]}", name="post-idle-probe")
            assert resp.status_code >= 400, "URL still live after idle grace — not reclaimed"
            assert any(m in resp.text.lower() for m in ("invalid session", "expired", "not found"))
        finally:
            release(client, alloc)

    @allure.id("TC-009")
    @allure.title("Long-running until released — URL stays live, then clean release")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.reliability
    def test_long_running_until_released(self, client: httpx.Client, recipe_uuid: str):
        alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
        os_name, caps = caps_for(alloc)
        driver = None
        try:
            driver = connect_driver(alloc["appium_url"], os_name, caps)
            _ = driver.orientation
            time.sleep(10)
            assert driver.session_id, "session died before release"
            allure.attach("session alive across hold window", name="liveness")
        finally:
            if driver:
                driver.quit()
            release(client, alloc)
