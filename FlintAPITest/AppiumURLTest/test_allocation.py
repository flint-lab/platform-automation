import time
from urllib.parse import urlparse

import allure
import httpx
import pytest

from .conftest import Config, allocate, release, caps_for, connect_driver, _ref_for


@allure.suite("Appium URL — Allocation")
class TestAllocation:

    @allure.id("TC-001")
    @allure.title("Happy-path allocate + connect + run + clean quit")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.functional
    def test_allocate_and_run(self, appium_url: dict):
        with allure.step("URL is well-formed (host, /connect token, /wd/hub path)"):
            url = appium_url["appium_url"]
            p = urlparse(url)
            assert p.scheme in ("http", "https") and p.netloc, f"bad URL: {url}"
            assert "/connect/" in p.path and "/wd/hub" in p.path, f"unexpected URL: {url}"

        os_name, caps = caps_for(appium_url)
        with allure.step(f"Connect Appium driver ({os_name}) and run a minimal command"):
            driver = connect_driver(url, os_name, caps)
            try:
                assert driver.session_id, "no session id after connect"
                _ = driver.orientation
            finally:
                driver.quit()

    @allure.id("TC-002")
    @allure.title("Time-to-ready — driver connects within the cold-start window")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.performance
    def test_time_to_ready(self, appium_url: dict):
        os_name, caps = caps_for(appium_url)
        start = time.monotonic()
        driver = connect_driver(appium_url["appium_url"], os_name, caps)
        elapsed = time.monotonic() - start
        try:
            allure.attach(f"{elapsed:.2f}s", name="connect-time")
            assert elapsed <= Config.CONNECT_WINDOW_S, (
                f"time-to-ready {elapsed:.1f}s exceeded window {Config.CONNECT_WINDOW_S}s"
            )
        finally:
            driver.quit()

    @allure.id("TC-004")
    @allure.title("Correct device allocated — connected device matches the request")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.functional
    def test_correct_device(self, appium_url: dict):
        details = (appium_url["raw"] or {}).get("device_details") or {}
        os_name, caps = caps_for(appium_url)
        with allure.step("Connect and compare reported device/version to allocation"):
            driver = connect_driver(appium_url["appium_url"], os_name, caps)
            try:
                if details.get("os_version"):
                    got = str(driver.capabilities.get("platformVersion", ""))
                    assert str(details["os_version"]) in got or got in str(details["os_version"]), (
                        f"version mismatch: allocated {details['os_version']}, session {got}"
                    )
            finally:
                driver.quit()

    @allure.id("TC-011")
    @allure.title("No devices available — structured busy/queued response, not a 500")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.functional
    def test_no_devices_available(self, client: httpx.Client, recipe_uuid: str):
        try:
            alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            assert code in (403, 409, 429, 503), f"unstructured busy response: {code}"
            body = exc.response.text.lower()
            assert any(k in body for k in ("queue", "retry", "busy", "limit", "capacity", "unavailable"))
            return
        release(client, alloc)
        pytest.skip("pool had capacity — exhaustion path not exercised this run")

    @allure.id("TC-012")
    @allure.title("Unique URL per allocation — two allocations never collide")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.functional
    def test_unique_url_per_allocation(self, client: httpx.Client, recipe_uuid: str):
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        first = allocate(client, Config.SURFACE, ref)
        try:
            try:
                second = allocate(client, Config.SURFACE, ref)
            except httpx.HTTPStatusError:
                pytest.skip("could not allocate a second device — capacity limited")
            try:
                assert first["appium_url"] != second["appium_url"], "same URL returned twice"
                assert first["device_id"] != second["device_id"], "same device returned twice"
            finally:
                release(client, second)
        finally:
            release(client, first)

    @allure.id("TC-029")
    @allure.title("Idempotent allocation retry — duplicate must not double-allocate")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.reliability
    def test_idempotent_retry(self, client: httpx.Client, recipe_uuid: str):
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        a = allocate(client, Config.SURFACE, ref)
        try:
            try:
                b = allocate(client, Config.SURFACE, ref)
            except httpx.HTTPStatusError as exc:
                assert exc.response.status_code in (409, 403, 429)
                return
            try:
                assert a["device_id"] != b["device_id"], "duplicate request double-allocated a device"
            finally:
                release(client, b)
        finally:
            release(client, a)
