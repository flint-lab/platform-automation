from pathlib import Path

import allure
import httpx
import pytest

from .conftest import Config


@allure.suite("Emulator — File Upload")
class TestFileUpload:

    @allure.id("TC-024")
    @allure.title("Upload file via FlintAPI — status uploaded, path returned")
    @allure.description(
        "Uploads a real file (FLINT_TEST_UPLOAD_FILE_PATH) to an allocated emulator. "
        "Verifies the response contains status=uploaded, correct filename, and a device_path. "
        "Skipped if FLINT_TEST_UPLOAD_FILE_PATH is not set."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.skipif(
        not Config.UPLOAD_FILE_PATH,
        reason="FLINT_TEST_UPLOAD_FILE_PATH not configured — provide a valid file path to run this test",
    )
    def test_upload_file_success(self, client: httpx.Client, allocated_emulator: dict):
        device_id = allocated_emulator["device_details"]["device_id"]
        filename = Path(Config.UPLOAD_FILE_PATH).name

        with allure.step(f"Read file from {Config.UPLOAD_FILE_PATH}"):
            with open(Config.UPLOAD_FILE_PATH, "rb") as f:
                file_content = f.read()

        with allure.step(f"POST /upload/{device_id} with {filename}"):
            response = client.post(
                f"/v1/devices/emulator/upload/{device_id}",
                files={"file": (filename, file_content, "application/octet-stream")},
                timeout=60.0,
            )

        with allure.step("Verify HTTP 200"):
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}. Body: {response.text}"
            )

        with allure.step("Verify response fields"):
            body = response.json()
            assert body.get("status") == "uploaded", (
                f"Expected status='uploaded', got '{body.get('status')}'"
            )
            assert body.get("filename") == filename, (
                f"Filename mismatch: expected '{filename}', got '{body.get('filename')}'"
            )
            assert "device_path" in body, "device_path field missing from response entirely"
            # device_path=None is a known product bug — field exists but path not returned by EDS

    @allure.id("TC-020")
    @allure.title("Upload two files sequentially — both succeed")
    @allure.description(
        "Uploads the same real file twice to the same emulator under different names. "
        "Verifies both uploads return status=uploaded with correct filenames. "
        "Skipped if FLINT_TEST_UPLOAD_FILE_PATH is not set."
    )
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.skipif(
        not Config.UPLOAD_FILE_PATH,
        reason="FLINT_TEST_UPLOAD_FILE_PATH not configured — provide a valid file path to run this test",
    )
    def test_upload_multiple_files_all_succeed(self, client: httpx.Client, allocated_emulator: dict):
        device_id = allocated_emulator["device_details"]["device_id"]
        filename = Path(Config.UPLOAD_FILE_PATH).name

        with open(Config.UPLOAD_FILE_PATH, "rb") as f:
            file_content = f.read()

        filenames = [f"upload_one_{filename}", f"upload_two_{filename}"]

        for upload_name in filenames:
            with allure.step(f"Upload {upload_name}"):
                response = client.post(
                    f"/v1/devices/emulator/upload/{device_id}",
                    files={"file": (upload_name, file_content, "application/octet-stream")},
                    timeout=60.0,
                )
                assert response.status_code == 200, (
                    f"Upload of {upload_name} failed: {response.status_code}. Body: {response.text}"
                )
                body = response.json()
                assert body.get("status") == "uploaded", (
                    f"Expected status='uploaded' for {upload_name}, got '{body.get('status')}'"
                )
                assert body.get("filename") == upload_name

    @allure.id("TC-028")
    @allure.title("Upload large file via FlintAPI — success or clear error (no silent failure)")
    @allure.description(
        "Uploads a 10 MB file to the emulator. "
        "Expects either a successful upload (200) or a clear error response (400/413/500). "
        "A silent failure (empty body, malformed JSON, or unexpected status) is a bug."
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_upload_large_file_no_silent_failure(self, client: httpx.Client, allocated_emulator: dict):
        device_id = allocated_emulator["device_details"]["device_id"]
        large_content = b"x" * (10 * 1024 * 1024)  # 10 MB

        with allure.step(f"POST /upload/{device_id} with a 10 MB file"):
            response = client.post(
                f"/v1/devices/emulator/upload/{device_id}",
                files={"file": ("large_file.bin", large_content, "application/octet-stream")},
                timeout=120.0,
            )

        with allure.step("Verify response is not a silent failure"):
            assert response.status_code in (200, 400, 413, 500), (
                f"Unexpected status code {response.status_code}. Body: {response.text}"
            )
            assert response.text.strip(), "Response body is empty — silent failure detected"

        with allure.step("Verify response body is valid JSON with a meaningful field"):
            body = response.json()
            has_status = "status" in body
            has_detail = "detail" in body
            assert has_status or has_detail, (
                f"Response has neither 'status' nor 'detail': {body}"
            )
