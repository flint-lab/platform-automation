import allure
import pytest
from selenium.common.exceptions import WebDriverException

from .conftest import caps_for, connect_driver


@allure.suite("Appium URL — Validation")
class TestValidation:

    @allure.id("TC-005")
    @allure.title("Capability mismatch caught early — wrong-OS caps fail at connect")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.functional
    def test_capability_mismatch(self, appium_url: dict):
        details = (appium_url["raw"] or {}).get("device_details") or {}
        device_os = (details.get("os") or "android").lower()
        wrong_os = "ios" if "android" in device_os else "android"
        _, caps = caps_for(appium_url, os_override=wrong_os)
        caps.pop("appium:udid", None)  # force the platform mismatch to surface

        with allure.step(f"Connect with {wrong_os} caps against the allocated device"):
            with pytest.raises(WebDriverException) as ei:
                driver = connect_driver(appium_url["appium_url"], wrong_os, caps)
                driver.quit()
        msg = str(ei.value).lower()
        allure.attach(msg[:400], name="error")
        assert any(
            m in msg for m in
            ("platform", "capabilit", "could not find", "invalid argument", "udid mismatch")
        ), f"mismatch produced a cryptic error: {msg[:200]}"
