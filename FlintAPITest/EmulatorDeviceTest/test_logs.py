import time

import allure
import httpx
import pytest

from .conftest import Config, allocate_emulator, stop_emulator

FINALIZE_WAIT = 5   # seconds after stop before downloading logs — lets server write logcat file


@allure.suite("Emulator — Logs")
class TestLogs:

    @allure.id("TC-045")
    @allure.title("Download logs after stopping emulator — file is valid and non-empty")
    @allure.description(
        "Allocates an emulator, uploads a real file to generate session activity, "
        "stops the emulator, waits for logs to be finalized, then downloads the logcat file. "
        "Verifies the response is 200, Content-Type is text/plain, and the file is not empty. "
        "Skipped if FLINT_TEST_UPLOAD_FILE_PATH is not set."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.skipif(
        not Config.UPLOAD_FILE_PATH,
        reason="FLINT_TEST_UPLOAD_FILE_PATH not configured — needed to generate session activity",
    )
    def test_download_logs_after_stop(self, client: httpx.Client, recipe_uuid: str):
        from pathlib import Path
        session = None
        try:
            with allure.step("Allocate emulator"):
                session = allocate_emulator(client, recipe_uuid)
                device_id = session["device_details"]["device_id"]
                session_id = session["session_id"]

            with allure.step("Generate session activity — upload a real file"):
                filename = Path(Config.UPLOAD_FILE_PATH).name
                with open(Config.UPLOAD_FILE_PATH, "rb") as f:
                    file_content = f.read()
                client.post(
                    f"/v1/devices/emulator/upload/{device_id}",
                    files={"file": (filename, file_content, "application/octet-stream")},
                    timeout=60.0,
                )

            with allure.step("Stop emulator"):
                stop_response = client.post(
                    f"/v1/devices/emulator/device/{device_id}/stop/session",
                    timeout=60.0,
                )
                assert stop_response.status_code == 200, (
                    f"Emulator stop failed: {stop_response.status_code}. Body: {stop_response.text}"
                )

            with allure.step(f"Wait {FINALIZE_WAIT}s for logcat file to be written"):
                time.sleep(FINALIZE_WAIT)

            with allure.step(f"GET /logs/download/{session_id}"):
                response = client.get(
                    f"/v1/devices/emulator/logs/download/{session_id}",
                    timeout=60.0,
                )

            with allure.step("Verify HTTP 200"):
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}. Body: {response.text}"
                )

            with allure.step("Verify Content-Type is text/plain"):
                content_type = response.headers.get("content-type", "")
                assert "text/plain" in content_type, (
                    f"Expected text/plain, got '{content_type}'"
                )

            with allure.step("Verify log file is not empty"):
                assert len(response.content) > 0, "Log file is empty — no logs were captured"

            with allure.step("Verify Content-Disposition suggests a .txt file"):
                disposition = response.headers.get("content-disposition", "")
                assert ".txt" in disposition, (
                    f"Expected .txt filename in Content-Disposition, got '{disposition}'"
                )

        finally:
            if session:
                stop_emulator(client, session["device_details"]["device_id"])
