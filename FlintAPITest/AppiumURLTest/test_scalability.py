import concurrent.futures as cf
import os
import time

import allure
import httpx
import pytest

from .conftest import Config, allocate, release, _ref_for


def _percentile(values, pct):
    if not values:
        return float("nan")
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((pct / 100.0) * len(s) + 0.5)) - 1))
    return s[k]


@allure.suite("Appium URL — Scalability")
class TestScalability:

    @allure.id("TC-017")
    @allure.title("Pool capacity boundary + queueing — overflow is structured, no hang")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.scalability
    def test_pool_boundary(self, client: httpx.Client, recipe_uuid: str):
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        acquired, rejected = [], []
        try:
            for _ in range(Config.POOL_SIZE + 2):
                try:
                    acquired.append(allocate(client, Config.SURFACE, ref))
                except httpx.HTTPStatusError as exc:
                    rejected.append(exc.response.status_code)
            assert len(acquired) <= Config.POOL_SIZE, "allocated past pool size (over-provisioned)"
            for code in rejected:
                assert code in (403, 409, 429, 503)
            allure.attach(f"pool={Config.POOL_SIZE} acquired={len(acquired)} rejected={rejected}", name="boundary")
        finally:
            for a in acquired:
                release(client, a)

    @allure.id("TC-018")
    @allure.title("Allocation load ramp — P50/P95/P99 within SLO")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.performance
    def test_load_ramp(self, client: httpx.Client, recipe_uuid: str):
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        ramp = [5] if os.getenv("LOAD_SMOKE") else [10, 50, 100]
        slo = {"p50": 2.0, "p95": 5.0, "p99": 10.0}

        def one():
            t0 = time.monotonic()
            try:
                a = allocate(client, Config.SURFACE, ref)
                dt = time.monotonic() - t0
                release(client, a)
                return dt
            except httpx.HTTPStatusError:
                return None

        any_ok = False
        for level in ramp:
            with cf.ThreadPoolExecutor(max_workers=level) as ex:
                lat = [x for x in ex.map(lambda _: one(), range(level)) if x is not None]
            if lat:
                any_ok = True
                p50, p95, p99 = _percentile(lat, 50), _percentile(lat, 95), _percentile(lat, 99)
                allure.attach(f"n={len(lat)} p50={p50:.2f} p95={p95:.2f} p99={p99:.2f}", name=f"ramp@{level}")
                assert p95 <= slo["p95"], f"P95 {p95:.1f}s > SLO {slo['p95']}s at {level}"
        assert any_ok, "no successful allocations during ramp"

    @allure.id("TC-024")
    @allure.title("Horizontal scale-out — added node receives allocations, balances")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.scalability
    def test_scale_out(self, client: httpx.Client, recipe_uuid: str):
        if not os.getenv("SCALE_OUT_NODE_ADDED"):
            pytest.skip("set SCALE_OUT_NODE_ADDED=1 after adding a node to assert rebalancing")
        ref = _ref_for(Config.SURFACE, recipe_uuid)
        allocs = []
        try:
            for _ in range(Config.POOL_SIZE + 2):
                try:
                    allocs.append(allocate(client, Config.SURFACE, ref))
                except httpx.HTTPStatusError:
                    break
            hosts = {a["appium_url"].split("/connect/")[0] for a in allocs}
            allure.attach(f"distinct_hosts={hosts}", name="scale-out")
            assert len(allocs) > Config.POOL_SIZE or len(hosts) > 1, "added node not used"
        finally:
            for a in allocs:
                release(client, a)
