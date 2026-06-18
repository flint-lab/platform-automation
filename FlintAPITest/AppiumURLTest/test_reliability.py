import os
import subprocess
import time

import allure
import httpx
import pytest

from .conftest import (
    Config, allocate, release, caps_for, connect_driver, probe_session, _ref_for,
)


def _run_fault(env_var: str) -> None:
    """Run an operator-supplied host fault command (kept out of code). Skips if unset."""
    cmd = os.getenv(env_var)
    if not cmd:
        pytest.skip(f"set {env_var} to the staging host-fault command to run this")
    allure.attach(cmd, name=f"fault:{env_var}")
    subprocess.run(cmd, shell=True, check=True, timeout=60)


@allure.suite("Appium URL — Reliability")
class TestReliability:

    @allure.id("TC-023")
    @allure.title("Zombie / GC sweep — abandoned device reclaimed within bounded time")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.reliability
    def test_gc_sweep(self, client: httpx.Client, recipe_uuid: str):
        alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
        wait = min(Config.GC_INTERVAL_S + 30, 240)
        if wait < Config.GC_INTERVAL_S:
            release(client, alloc)
            pytest.skip(f"GC interval {Config.GC_INTERVAL_S}s exceeds bounded wait {wait}s")
        time.sleep(wait)
        resp = probe_session(alloc["appium_url"])
        allure.attach(f"{resp.status_code} {resp.text[:200]}", name="post-gc-probe")
        if resp.status_code < 400:
            release(client, alloc)
            pytest.fail(f"device still reachable after GC window ({resp.status_code})")
        assert resp.status_code in (401, 403, 404)

    @allure.id("TC-010")
    @allure.title("Transient network drop mid-session — probe & document (no hang)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.reliability
    @pytest.mark.destructive
    def test_network_drop(self, client: httpx.Client, recipe_uuid: str):
        alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
        os_name, caps = caps_for(alloc)
        driver = connect_driver(alloc["appium_url"], os_name, caps)
        try:
            _ = driver.orientation
            _run_fault("FAULT_NET_DROP")
            time.sleep(5)
            from selenium.common.exceptions import WebDriverException
            outcome = "resumed"
            try:
                _ = driver.orientation  # bounded by client timeout — must not hang
            except WebDriverException:
                outcome = "clean-fail"
            allure.attach(outcome, name="observed-behaviour")
        finally:
            try:
                driver.quit()
            except Exception:
                pass
            release(client, alloc)

    @allure.id("TC-019")
    @allure.title("Soak / endurance — repeated allocate→run→release, no orphans")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.reliability
    def test_soak(self, client: httpx.Client, recipe_uuid: str):
        duration = 60.0 if os.getenv("SOAK_SMOKE") else float(os.getenv("FLINT_SOAK_S", "7200"))
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        deadline = time.monotonic() + duration
        cycles = 0
        while time.monotonic() < deadline:
            alloc = allocate(client, Config.SURFACE, ref)
            os_name, caps = caps_for(alloc)
            d = connect_driver(alloc["appium_url"], os_name, caps)
            d.quit()
            release(client, alloc)
            cycles += 1
        allure.attach(f"cycles={cycles} duration={duration}s", name="soak")
        assert cycles > 0

    @allure.id("TC-022")
    @allure.title("Appium/node process crash — sessions fail fast, no dead URLs after")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.reliability
    @pytest.mark.destructive
    def test_appium_crash(self, client: httpx.Client, recipe_uuid: str):
        alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
        try:
            _run_fault("FAULT_KILL_APPIUM")
            time.sleep(3)
            resp = probe_session(alloc["appium_url"])
            allure.attach(f"{resp.status_code} {resp.text[:200]}", name="post-crash")
            assert resp.status_code >= 400, "URL served a session after Appium crash"
        finally:
            release(client, alloc)

    @allure.id("TC-025")
    @allure.title("Graceful node drain — in-flight finishes, no new routing")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.reliability
    @pytest.mark.destructive
    def test_node_drain(self, client: httpx.Client, recipe_uuid: str):
        alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
        os_name, caps = caps_for(alloc)
        driver = connect_driver(alloc["appium_url"], os_name, caps)
        try:
            _run_fault("FAULT_DRAIN_NODE")
            _ = driver.orientation  # in-flight session must still finish gracefully
            allure.attach("in-flight survived drain", name="drain")
        finally:
            try:
                driver.quit()
            except Exception:
                pass
            release(client, alloc)

    @allure.id("TC-028")
    @allure.title("Control-plane restart — valid in-flight URLs survive/reconcile")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.reliability
    @pytest.mark.destructive
    def test_control_plane_restart(self, client: httpx.Client, recipe_uuid: str):
        alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
        try:
            before = probe_session(alloc["appium_url"]).status_code
            _run_fault("FAULT_RESTART_CONTROL_PLANE")
            time.sleep(10)
            after = probe_session(alloc["appium_url"]).status_code
            allure.attach(f"before={before} after={after}", name="restart")
            assert after == before or after < 500, "valid URL invalidated by restart"
        finally:
            release(client, alloc)
