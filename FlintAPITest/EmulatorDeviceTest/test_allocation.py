import allure
import httpx
import pytest

from .conftest import Config, allocate_emulator, stop_emulator


@allure.suite("Emulator — Allocation")
class TestAllocation:

    @allure.id("TC-001")
    @allure.title("Allocate emulator — session created with all required fields")
    @allure.description(
        "Allocates an emulator using a recipe UUID fetched from /list. "
        "Verifies the response contains session_id, device_details, adb_url, "
        "file_upload_url, and appium_configuration."
    )
    @allure.severity(allure.severity_level.BLOCKER)
    def test_allocate_emulator_success(self, client: httpx.Client, recipe_uuid: str):
        session = None
        try:
            with allure.step("POST /allocate-emulator with recipe UUID from /list"):
                session = allocate_emulator(client, recipe_uuid)

            with allure.step("Verify top-level session fields"):
                assert session.get("session_id"), "session_id is missing or empty"
                assert session.get("started_at"), "started_at is missing"
                assert session.get("adb_url"), "adb_url is missing"
                assert session.get("file_upload_url"), "file_upload_url is missing"

            with allure.step("Verify device_details fields"):
                device = session.get("device_details", {})
                assert device.get("device_id"), "device_details.device_id is missing"
                assert device.get("recipe_uuid") == recipe_uuid, (
                    f"recipe_uuid mismatch: expected {recipe_uuid}, got {device.get('recipe_uuid')}"
                )
                assert device.get("os"), "device_details.os is missing"

            with allure.step("Verify appium_configuration fields"):
                appium = session.get("appium_configuration", {})
                assert appium.get("appium_url"), "appium_configuration.appium_url is missing"
                assert appium.get("token"), "appium_configuration.token is missing"
                assert appium.get("device_id"), "appium_configuration.device_id is missing"

        finally:
            if session:
                with allure.step("Stop emulator (cleanup)"):
                    stop_emulator(client, session["device_details"]["device_id"])

    @allure.id("TC-002")
    @allure.title("Allocate with non-existent recipe UUID — 404 returned")
    @allure.description(
        "Attempts to allocate an emulator using a UUID that does not exist. "
        "Expects a 404 response with no session created."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    def test_allocate_nonexistent_recipe_uuid_returns_404(self, client: httpx.Client):
        invalid_uuid = "00000000-0000-0000-0000-000000000000"

        with allure.step(f"POST /allocate-emulator with invalid UUID: {invalid_uuid}"):
            response = client.post(
                "/v1/devices/emulator/allocate-emulator",
                params={"recipe_uuid": invalid_uuid},
                timeout=30.0,
            )

        with allure.step("Verify response is 404"):
            assert response.status_code == 404, (
                f"Expected 404, got {response.status_code}. Body: {response.text}"
            )

        with allure.step("Verify error detail is present in response body"):
            body = response.json()
            assert "detail" in body, f"No 'detail' field in error response: {body}"
