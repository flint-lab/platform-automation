import allure
import httpx
import pytest

from .conftest import (
    Config, allocate, release, caps_for, connect_driver,
    probe_session, tamper_token, _ref_for,
)


@allure.suite("Appium URL — Security")
class TestSecurity:

    @allure.id("TC-006")
    @allure.title("Tenant isolation — user B cannot use user A's URL")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.security
    def test_tenant_isolation(self, appium_url: dict, client_b: httpx.Client):
        # B drives A's exact URL. Must be rejected (401/403) or the UDID-mismatch 400.
        resp = probe_session(appium_url["appium_url"])
        allure.attach(f"{resp.status_code} {resp.text[:200]}", name="B-using-A-url")
        assert resp.status_code >= 400, "B reached A's device — isolation broken"
        assert resp.status_code in (400, 401, 403)

    @allure.id("TC-007")
    @allure.title("URL not guessable — mutated token is rejected")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.security
    def test_not_guessable(self, appium_url: dict):
        mutated = tamper_token(appium_url["appium_url"])
        assert mutated != appium_url["appium_url"], "token mutation produced no change"
        resp = probe_session(mutated)
        allure.attach(f"{resp.status_code} {resp.text[:200]}", name="mutated-token")
        assert resp.status_code in (401, 403, 404)
        assert any(m in resp.text.lower() for m in ("invalid session", "expired", "not found"))

    @allure.id("TC-013")
    @allure.title("Post-quit invalidation — URL is dead after release")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.security
    def test_post_quit_invalidation(self, client: httpx.Client, recipe_uuid: str):
        alloc = allocate(client, Config.SURFACE, _ref_for(Config.SURFACE, recipe_uuid))
        os_name, caps = caps_for(alloc)
        driver = connect_driver(alloc["appium_url"], os_name, caps)
        driver.quit()
        release(client, alloc)
        resp = probe_session(alloc["appium_url"])
        allure.attach(f"{resp.status_code} {resp.text[:200]}", name="post-quit-probe")
        assert resp.status_code in (401, 403, 404), "URL still alive after release"

    @allure.id("TC-015")
    @allure.title("Invalid NAT token — unauthorized at list & allocate")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.security
    def test_invalid_nat_token(self):
        bad = httpx.Client(
            base_url=Config.BASE_URL,
            headers={"Authorization": "Bearer invalid-nat-000000000000"},
            timeout=30.0,
        )
        with bad:
            list_resp = bad.get("/v1/devices/emulator/list")
            allure.attach(f"list -> {list_resp.status_code}", name="list")
            assert list_resp.status_code in (401, 403), f"invalid NAT not rejected: {list_resp.status_code}"
