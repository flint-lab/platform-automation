import concurrent.futures as cf
import os

import allure
import httpx
import pytest

from .conftest import Config

METRIC_HINTS = ("alloc", "queue", "session", "utiliz", "fail")


@allure.suite("Appium URL — Observability & Rate limiting")
class TestObservability:

    @allure.id("TC-027")
    @allure.title("Rate limiting / burst protection — 429 under burst, control plane healthy")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.security
    def test_rate_limit_burst(self, client: httpx.Client):
        burst = Config.RATE_LIMIT_PER_SECOND * 3

        def hit():
            return client.get("/v1/devices/emulator/list", timeout=30.0).status_code

        with cf.ThreadPoolExecutor(max_workers=min(burst, 64)) as ex:
            statuses = list(ex.map(lambda _: hit(), range(burst)))
        allure.attach(f"burst={burst} 429s={statuses.count(429)}", name="burst")
        assert statuses.count(429) > 0, f"burst of {burst} produced no 429 — not throttled"
        assert all(s < 500 for s in statuses), "5xx during burst — control plane unhealthy"

    @allure.id("TC-030")
    @allure.title("Metrics & tracing coverage — required signals present")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.observability
    def test_metrics_coverage(self):
        metrics_url = os.getenv("FLINT_METRICS_URL")
        if not metrics_url:
            pytest.skip("set FLINT_METRICS_URL (e.g. http://host:8024/metrics) to run TC-030")
        resp = httpx.get(metrics_url, timeout=30.0)
        assert resp.status_code == 200, f"metrics endpoint -> {resp.status_code}"
        body = resp.text.lower()
        missing = [h for h in METRIC_HINTS if h not in body]
        allure.attach(f"missing={missing}", name="metrics")
        assert not missing, f"metrics missing required signals: {missing}"
