import concurrent.futures as cf

import allure
import httpx
import pytest

from .conftest import Config, allocate, release, caps_for, connect_driver, _ref_for


@allure.suite("Appium URL — Concurrency")
class TestConcurrency:

    @allure.id("TC-014")
    @allure.title("Parallel suite isolation — two users, two URLs, full isolation")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.functional
    def test_parallel_isolation(self, client: httpx.Client, client_b: httpx.Client, recipe_uuid: str):
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        a = allocate(client, Config.SURFACE, ref)
        b = allocate(client_b, Config.SURFACE, ref)
        try:
            assert a["appium_url"] != b["appium_url"], "two users got the same URL"
            assert a["device_id"] != b["device_id"], "two users share one device"

            def drive(alloc):
                os_name, caps = caps_for(alloc)
                d = connect_driver(alloc["appium_url"], os_name, caps)
                try:
                    return d.session_id
                finally:
                    d.quit()

            with cf.ThreadPoolExecutor(max_workers=2) as ex:
                sid_a = ex.submit(drive, a).result(timeout=Config.CONNECT_WINDOW_S + 60)
                sid_b = ex.submit(drive, b).result(timeout=Config.CONNECT_WINDOW_S + 60)
            assert sid_a != sid_b, "sessions collided across users"
        finally:
            release(client, a)
            release(client_b, b)

    @allure.id("TC-020")
    @allure.title("Race for the last device — exactly one wins, no double-alloc")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.reliability
    def test_race_last_device(self, client: httpx.Client, recipe_uuid: str):
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        wins, errors = [], []
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            futs = [ex.submit(allocate, client, Config.SURFACE, ref) for _ in range(2)]
            for f in cf.as_completed(futs, timeout=180):
                try:
                    wins.append(f.result())
                except httpx.HTTPStatusError as exc:
                    errors.append(exc.response.status_code)
        try:
            ids = [w["device_id"] for w in wins]
            assert len(ids) == len(set(ids)), f"same device double-allocated: {ids}"
            for code in errors:
                assert code in (403, 409, 429, 503)
            allure.attach(f"won={len(wins)} rejected={errors}", name="race-outcome")
        finally:
            for w in wins:
                release(client, w)

    @allure.id("TC-016")
    @allure.title("Per-tenant concurrency cap — cap+1 is rejected, never over-provisioned")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.scalability
    def test_per_tenant_cap(self, client: httpx.Client, recipe_uuid: str):
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        acquired, rejected = [], []
        try:
            for _ in range(Config.CONCURRENCY_CAP + 1):
                try:
                    acquired.append(allocate(client, Config.SURFACE, ref))
                except httpx.HTTPStatusError as exc:
                    rejected.append(exc.response.status_code)
            assert len(acquired) <= Config.CONCURRENCY_CAP, "over-provisioned past the plan cap"
            assert rejected, "cap+1 was not rejected"
            assert rejected[-1] in (403, 409, 429)
        finally:
            for a in acquired:
                release(client, a)

    @allure.id("TC-026")
    @allure.title("Multiple devices for one customer run concurrently")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.scalability
    def test_multi_device_one_customer(self, client: httpx.Client, recipe_uuid: str):
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        target = max(2, Config.CONCURRENCY_CAP)
        allocs = []
        try:
            with cf.ThreadPoolExecutor(max_workers=target) as ex:
                futs = [ex.submit(allocate, client, Config.SURFACE, ref) for _ in range(target)]
                for f in cf.as_completed(futs, timeout=300):
                    try:
                        allocs.append(f.result())
                    except httpx.HTTPStatusError as exc:
                        assert exc.response.status_code in (403, 409, 429, 503)
            urls = {a["appium_url"] for a in allocs}
            assert len(urls) == len(allocs), "concurrent devices shared a URL"
        finally:
            for a in allocs:
                release(client, a)
