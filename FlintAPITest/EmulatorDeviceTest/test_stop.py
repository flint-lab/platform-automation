import allure
import httpx

from .conftest import allocate_emulator, stop_emulator


@allure.suite("Emulator — Stop")
class TestStop:

    @allure.id("TC-021")
    @allure.title("Deallocate emulator — session ended, response fields valid")
    @allure.description(
        "Allocates an emulator, then stops it via the stop endpoint. "
        "Verifies the response contains device_id, session_id, status, and deallocated_at. "
        "Confirms the emulator is no longer accessible after stop."
    )
    @allure.severity(allure.severity_level.BLOCKER)
    def test_stop_emulator_returns_valid_response(self, client: httpx.Client, recipe_uuid: str):
        with allure.step("Allocate emulator"):
            session = allocate_emulator(client, recipe_uuid)
            device_id = session["device_details"]["device_id"]
            session_id = session["session_id"]

        with allure.step(f"POST /device/{device_id}/stop/session"):
            response = client.post(
                f"/v1/devices/emulator/device/{device_id}/stop/session",
                timeout=60.0,
            )

        with allure.step("Verify HTTP 200"):
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}. Body: {response.text}"
            )

        with allure.step("Verify response body fields"):
            body = response.json()
            assert body.get("device_id") == device_id, (
                f"device_id mismatch: expected {device_id}, got {body.get('device_id')}"
            )
            assert body.get("session_id") == session_id, (
                f"session_id mismatch: expected {session_id}, got {body.get('session_id')}"
            )
            assert body.get("status"), "status field is missing or empty"
            assert body.get("deallocated_at"), "deallocated_at is missing"

        with allure.step("Verify emulator is no longer active — second stop returns error"):
            second_stop = client.post(
                f"/v1/devices/emulator/device/{device_id}/stop/session",
                timeout=30.0,
            )
            assert second_stop.status_code != 200, (
                "Expected an error when stopping an already-stopped emulator, "
                f"but got {second_stop.status_code}"
            )
