import allure
import httpx
import pytest

from pathlib import Path

from pathlib import Path

from .conftest import Config


@allure.suite("Emulator — APK Install")
class TestApkInstall:

    @allure.id("TC-025")
    @allure.title("Install valid APK via FlintAPI — status success")
    @allure.description(
        "Installs a real APK on the allocated emulator. "
        "Verifies the response returns status=success and a package_name. "
        "Skipped if FLINT_TEST_APK_PATH is not set in the environment."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.skipif(
        not Config.APK_PATH,
        reason="FLINT_TEST_APK_PATH not configured — provide a valid APK path to run this test",
    )
    def test_install_valid_apk_success(self, client: httpx.Client, allocated_emulator: dict):
        device_id = allocated_emulator["device_details"]["device_id"]

        with allure.step(f"Read APK from {Config.APK_PATH}"):
            with open(Config.APK_PATH, "rb") as f:
                apk_bytes = f.read()

        with allure.step(f"POST /install-apk/{device_id}"):
            response = client.post(
                f"/v1/devices/emulator/install-apk/{device_id}",
                files={"file": ("app.apk", apk_bytes, "application/vnd.android.package-archive")},
                timeout=120.0,
            )

        with allure.step("Verify HTTP 200 and status=success"):
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}. Body: {response.text}"
            )
            body = response.json()
            assert body.get("status") == "success", (
                f"Expected status='success', got '{body.get('status')}'"
            )
            assert body.get("package_name"), "package_name is missing from response"

    @allure.id("TC-019")
    @allure.title("Install corrupted APK — error returned, emulator session stays alive")
    @allure.description(
        "Sends a file with .apk extension but invalid/corrupted content. "
        "Expects an error response. Then verifies the emulator session is still alive "
        "by confirming the stop endpoint still works."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    def test_install_corrupted_apk_error_session_alive(
        self, client: httpx.Client, allocated_emulator: dict
    ):
        device_id = allocated_emulator["device_details"]["device_id"]
        corrupted_content = b"this is not a valid apk"

        with allure.step(f"POST /install-apk/{device_id} with corrupted content"):
            response = client.post(
                f"/v1/devices/emulator/install-apk/{device_id}",
                files={"file": ("corrupted.apk", corrupted_content, "application/vnd.android.package-archive")},
                timeout=60.0,
            )

        with allure.step("Verify install failed with an error response"):
            assert response.status_code in (400, 500), (
                f"Expected 400 or 500 for corrupted APK, got {response.status_code}. "
                f"Body: {response.text}"
            )
            body = response.json()
            assert "detail" in body, f"Error response missing 'detail' field: {body}"

        with allure.step("Verify emulator session is still alive — stop endpoint works"):
            stop_response = client.post(
                f"/v1/devices/emulator/device/{device_id}/stop/session",
                timeout=30.0,
            )
            assert stop_response.status_code == 200, (
                f"Emulator session died after failed APK install. "
                f"Stop returned {stop_response.status_code}. Body: {stop_response.text}"
            )

        # Mark already stopped so the fixture cleanup does not double-stop
        allocated_emulator["_stopped"] = True

    @allure.id("TC-027")
    @allure.title("Install corrupted APK via FlintAPI — clear error, device unaffected")
    @allure.description(
        "Sends a non-.apk file to the install endpoint. "
        "Expects a 400 rejection. Device should remain usable (file upload still works)."
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_install_wrong_extension_rejected(self, client: httpx.Client, allocated_emulator: dict):
        device_id = allocated_emulator["device_details"]["device_id"]

        with allure.step(f"POST /install-apk/{device_id} with .zip extension instead of .apk"):
            response = client.post(
                f"/v1/devices/emulator/install-apk/{device_id}",
                files={"file": ("app.zip", b"fake content", "application/zip")},
                timeout=30.0,
            )

        with allure.step("Verify 400 — wrong file type rejected"):
            assert response.status_code == 400, (
                f"Expected 400 for wrong extension, got {response.status_code}. Body: {response.text}"
            )

        with allure.step("Verify device is unaffected — file upload still works"):
            if not Config.UPLOAD_FILE_PATH:
                pytest.skip("FLINT_TEST_UPLOAD_FILE_PATH not set — cannot verify device health after rejection")
            filename = Path(Config.UPLOAD_FILE_PATH).name
            with open(Config.UPLOAD_FILE_PATH, "rb") as f:
                upload_bytes = f.read()
            upload = client.post(
                f"/v1/devices/emulator/upload/{device_id}",
                files={"file": (filename, upload_bytes, "application/octet-stream")},
                timeout=60.0,
            )
            assert upload.status_code == 200, (
                f"Device affected after rejected install — upload returned {upload.status_code}. Body: {upload.text}"
            )

    @allure.id("TC-029")
    @allure.title("Install same APK twice — overwritten or clear error, no crash")
    @allure.description(
        "Installs an APK on an emulator, then installs the same APK again. "
        "Expects either a successful overwrite or a clear error. "
        "No crash or 5xx without detail is acceptable. "
        "Skipped if FLINT_TEST_APK_PATH is not set."
    )
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.skipif(
        not Config.APK_PATH,
        reason="FLINT_TEST_APK_PATH not configured — provide a valid APK path to run this test",
    )
    def test_install_same_apk_twice_handled(self, client: httpx.Client, allocated_emulator: dict):
        device_id = allocated_emulator["device_details"]["device_id"]

        with open(Config.APK_PATH, "rb") as f:
            apk_bytes = f.read()

        with allure.step("First install"):
            first = client.post(
                f"/v1/devices/emulator/install-apk/{device_id}",
                files={"file": ("app.apk", apk_bytes, "application/vnd.android.package-archive")},
                timeout=120.0,
            )
            assert first.status_code == 200, (
                f"First install failed: {first.status_code}. Body: {first.text}"
            )

        with allure.step("Second install (same APK)"):
            second = client.post(
                f"/v1/devices/emulator/install-apk/{device_id}",
                files={"file": ("app.apk", apk_bytes, "application/vnd.android.package-archive")},
                timeout=120.0,
            )

        with allure.step("Verify second install is handled — overwrite success or clear error"):
            assert second.status_code in (200, 400, 409, 500), (
                f"Unexpected status {second.status_code} on second install. Body: {second.text}"
            )
            body = second.json()
            if second.status_code == 200:
                assert body.get("status") == "success", f"Unexpected body on second install: {body}"
            else:
                assert "detail" in body, (
                    f"Error response on second install missing 'detail': {body}"
                )
