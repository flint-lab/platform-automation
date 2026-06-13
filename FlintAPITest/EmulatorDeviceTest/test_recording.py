import io
import time
import zipfile

import allure
import httpx

RECORD_DURATION = 5   # seconds to record before stopping — ensures file has content
FINALIZE_WAIT = 3     # seconds after stop before downloading — lets server finalize the file


def _start_recording(client: httpx.Client, session_id: str) -> dict:
    response = client.post(
        f"/v1/devices/emulator/record/start/{session_id}",
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def _stop_recording(client: httpx.Client, session_id: str) -> dict:
    response = client.post(
        f"/v1/devices/emulator/record/stop/{session_id}",
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()


@allure.suite("Emulator — Recording")
class TestRecording:

    @allure.id("TC-030")
    @allure.title("Start and stop recording — recording_id and filename returned")
    @allure.description(
        "Starts a recording, waits briefly, then stops it. "
        "Verifies start returns recording_id and status=started. "
        "Verifies stop returns recording_id, filename, and status=stopped."
    )
    @allure.severity(allure.severity_level.BLOCKER)
    def test_start_and_stop_recording(self, client: httpx.Client, allocated_emulator: dict):
        session_id = allocated_emulator["session_id"]

        with allure.step(f"POST /record/start/{session_id}"):
            start = _start_recording(client, session_id)

        with allure.step("Verify start response fields"):
            assert start.get("recording_id"), "recording_id missing from start response"
            assert start.get("device_id"), "device_id missing from start response"
            assert start.get("status") == "started", (
                f"Expected status='started', got '{start.get('status')}'"
            )
            assert start.get("started_at"), "started_at missing"

        with allure.step(f"Wait {RECORD_DURATION}s to capture content"):
            time.sleep(RECORD_DURATION)

        with allure.step(f"POST /record/stop/{session_id}"):
            stop = _stop_recording(client, session_id)

        with allure.step("Verify stop response fields"):
            assert stop.get("recording_id") == start["recording_id"], (
                "recording_id mismatch between start and stop"
            )
            assert stop.get("status") == "stopped", (
                f"Expected status='stopped', got '{stop.get('status')}'"
            )
            assert stop.get("filename"), "filename missing from stop response"
            assert stop.get("stopped_at"), "stopped_at missing"

    @allure.id("TC-031")
    @allure.title("Download recording — bytes received, Content-Type is video/mp4")
    @allure.description(
        "Starts and stops a recording, then downloads it. "
        "Verifies the download returns bytes with Content-Type video/mp4."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    def test_download_recording_valid_mp4(self, client: httpx.Client, allocated_emulator: dict):
        session_id = allocated_emulator["session_id"]

        with allure.step("Start recording"):
            _start_recording(client, session_id)

        with allure.step(f"Wait {RECORD_DURATION}s to capture content"):
            time.sleep(RECORD_DURATION)

        with allure.step("Stop recording"):
            stop = _stop_recording(client, session_id)
            filename = stop["filename"]

        with allure.step(f"Wait {FINALIZE_WAIT}s for file to be finalized on server"):
            time.sleep(FINALIZE_WAIT)

        with allure.step(f"GET /record/download/{session_id}/{filename}"):
            response = client.get(
                f"/v1/devices/emulator/record/download/{session_id}/{filename}",
                timeout=120.0,
            )

        with allure.step("Verify HTTP 200"):
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}. Body: {response.text}"
            )

        with allure.step("Verify Content-Type is video/mp4"):
            content_type = response.headers.get("content-type", "")
            assert "video/mp4" in content_type, (
                f"Expected Content-Type video/mp4, got '{content_type}'"
            )

        with allure.step("Verify response body is non-empty"):
            assert len(response.content) > 0, "Downloaded recording file is empty"

    @allure.id("TC-035")
    @allure.title("Three separate recordings in one session — all return filenames")
    @allure.description(
        "Starts and stops three separate recordings in sequence on the same session. "
        "Verifies each stop response returns a unique filename."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    def test_multiple_recordings_all_saved(self, client: httpx.Client, allocated_emulator: dict):
        session_id = allocated_emulator["session_id"]
        filenames = []

        for i in range(1, 4):
            with allure.step(f"Recording {i}: start"):
                _start_recording(client, session_id)

            with allure.step(f"Recording {i}: wait {RECORD_DURATION}s"):
                time.sleep(RECORD_DURATION)

            with allure.step(f"Recording {i}: stop"):
                stop = _stop_recording(client, session_id)
                filename = stop.get("filename")
                assert filename, f"Recording {i} stop response missing filename"
                filenames.append(filename)

        with allure.step("Verify all 3 filenames are present and unique"):
            assert len(filenames) == 3, f"Expected 3 filenames, got {len(filenames)}"
            assert len(set(filenames)) == 3, (
                f"Expected 3 unique filenames but got duplicates: {filenames}"
            )

    @allure.id("TC-036")
    @allure.title("Download each of three recordings individually — correct file each time")
    @allure.description(
        "After recording three sessions, downloads each one individually and "
        "verifies each download returns a non-empty MP4 response."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    def test_download_each_recording_individually(
        self, client: httpx.Client, allocated_emulator: dict
    ):
        session_id = allocated_emulator["session_id"]
        filenames = []

        for i in range(1, 4):
            _start_recording(client, session_id)
            time.sleep(RECORD_DURATION)
            stop = _stop_recording(client, session_id)
            filenames.append(stop["filename"])

        time.sleep(FINALIZE_WAIT)

        for filename in filenames:
            with allure.step(f"Download {filename}"):
                response = client.get(
                    f"/v1/devices/emulator/record/download/{session_id}/{filename}",
                    timeout=120.0,
                )
                assert response.status_code == 200, (
                    f"Download of {filename} failed: {response.status_code}"
                )
                assert len(response.content) > 0, f"Download of {filename} returned empty file"
                assert "video/mp4" in response.headers.get("content-type", ""), (
                    f"Wrong Content-Type for {filename}: {response.headers.get('content-type')}"
                )

    @allure.id("TC-037")
    @allure.title("Download all recordings as ZIP — valid archive with all files")
    @allure.description(
        "Creates multiple recordings and downloads them as a ZIP archive. "
        "Verifies the ZIP is valid and contains the expected number of files."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    def test_download_all_recordings_as_zip(self, client: httpx.Client, allocated_emulator: dict):
        session_id = allocated_emulator["session_id"]
        recording_count = 2

        for _ in range(recording_count):
            _start_recording(client, session_id)
            time.sleep(RECORD_DURATION)
            _stop_recording(client, session_id)

        time.sleep(FINALIZE_WAIT)

        with allure.step(f"GET /record/download-all/{session_id}"):
            response = client.get(
                f"/v1/devices/emulator/record/download-all/{session_id}",
                timeout=180.0,
            )

        with allure.step("Verify HTTP 200"):
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}. Body: {response.text}"
            )

        with allure.step("Verify response is a valid ZIP archive"):
            assert zipfile.is_zipfile(io.BytesIO(response.content)), (
                "Response body is not a valid ZIP file"
            )

        with allure.step(f"Verify ZIP contains {recording_count} file(s)"):
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                entries = zf.namelist()
                assert len(entries) >= recording_count, (
                    f"Expected at least {recording_count} files in ZIP, found {len(entries)}: {entries}"
                )

    @allure.id("TC-038")
    @allure.title("Near-zero length recording — no crash, response returned")
    @allure.description(
        "Starts a recording and stops it immediately without any delay. "
        "Verifies neither call crashes and the session remains alive."
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_near_zero_length_recording_no_crash(
        self, client: httpx.Client, allocated_emulator: dict
    ):
        session_id = allocated_emulator["session_id"]

        with allure.step("Start recording"):
            start_response = client.post(
                f"/v1/devices/emulator/record/start/{session_id}",
                timeout=30.0,
            )
            assert start_response.status_code == 200, (
                f"Start failed: {start_response.status_code}. Body: {start_response.text}"
            )

        with allure.step("Stop recording immediately — no delay intentional"):
            stop_response = client.post(
                f"/v1/devices/emulator/record/stop/{session_id}",
                timeout=60.0,
            )

        with allure.step("Verify stop did not crash (200 or meaningful error)"):
            assert stop_response.status_code in (200, 400, 422), (
                f"Unexpected status {stop_response.status_code} on near-zero recording stop. "
                f"Body: {stop_response.text}"
            )
            assert stop_response.text.strip(), "Stop response body is empty"

    @allure.id("TC-041")
    @allure.title("Stop emulator while recording active — recording is saved")
    @allure.description(
        "Starts a recording and then stops the emulator without explicitly stopping the recording first. "
        "Verifies the recording is preserved and available via download-all."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    def test_recording_saved_when_emulator_stopped(
        self, client: httpx.Client, allocated_emulator: dict
    ):
        session_id = allocated_emulator["session_id"]
        device_id = allocated_emulator["device_details"]["device_id"]

        with allure.step("Start recording"):
            _start_recording(client, session_id)

        with allure.step(f"Wait {RECORD_DURATION}s to capture content"):
            time.sleep(RECORD_DURATION)

        with allure.step("Stop emulator without stopping recording first"):
            stop_response = client.post(
                f"/v1/devices/emulator/device/{device_id}/stop/session",
                timeout=60.0,
            )
            assert stop_response.status_code == 200, (
                f"Emulator stop failed: {stop_response.status_code}. Body: {stop_response.text}"
            )

        with allure.step(f"Wait {FINALIZE_WAIT}s for recording to be finalized"):
            time.sleep(FINALIZE_WAIT)

        with allure.step("Verify recording was saved — download-all returns a non-empty ZIP"):
            download = client.get(
                f"/v1/devices/emulator/record/download-all/{session_id}",
                timeout=60.0,
            )
            assert download.status_code == 200, (
                f"Recording not accessible after emulator stop: {download.status_code}. "
                f"Body: {download.text}"
            )
            assert len(download.content) > 0, "Recording file is empty after emulator stop"
            assert zipfile.is_zipfile(io.BytesIO(download.content)), (
                "download-all response is not a valid ZIP — recording may not have been saved"
            )

        # Emulator already stopped — prevent fixture from double-stopping
        allocated_emulator["_stopped"] = True

    @allure.id("TC-042")
    @allure.title("Download completed recording while another is still running")
    @allure.description(
        "Stops Recording-1, then starts Recording-2 and keeps it running. "
        "Downloads Recording-1 while Recording-2 is still active and verifies it downloads correctly."
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_download_completed_recording_while_another_runs(
        self, client: httpx.Client, allocated_emulator: dict
    ):
        session_id = allocated_emulator["session_id"]

        with allure.step("Start Recording-1"):
            _start_recording(client, session_id)

        with allure.step(f"Wait {RECORD_DURATION}s to capture content"):
            time.sleep(RECORD_DURATION)

        with allure.step("Stop Recording-1"):
            stop1 = _stop_recording(client, session_id)
            filename1 = stop1["filename"]

        with allure.step(f"Wait {FINALIZE_WAIT}s for file to be finalized"):
            time.sleep(FINALIZE_WAIT)

        with allure.step("Start Recording-2 (keep running)"):
            _start_recording(client, session_id)

        with allure.step(f"Download Recording-1 ({filename1}) while Recording-2 is active"):
            response = client.get(
                f"/v1/devices/emulator/record/download/{session_id}/{filename1}",
                timeout=120.0,
            )
            assert response.status_code == 200, (
                f"Download of Recording-1 failed while Recording-2 was running: "
                f"{response.status_code}. Body: {response.text}"
            )
            assert len(response.content) > 0, "Recording-1 downloaded as empty file"

        with allure.step("Stop Recording-2"):
            _stop_recording(client, session_id)

    @allure.id("TC-043")
    @allure.title("Start recording when one is already active — handled correctly, no silent failure")
    @allure.description(
        "Starts a recording then immediately attempts to start another. "
        "Expects either a new recording is created (200) or a clear error (409/400/500 with detail). "
        "A silent failure (empty body or unexpected status) is a bug."
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_start_recording_when_already_active(
        self, client: httpx.Client, allocated_emulator: dict
    ):
        session_id = allocated_emulator["session_id"]

        with allure.step("Start Recording-1"):
            _start_recording(client, session_id)

        with allure.step("Attempt to start Recording-2 while Recording-1 is active"):
            second_start = client.post(
                f"/v1/devices/emulator/record/start/{session_id}",
                timeout=30.0,
            )

        with allure.step("Verify no silent failure — response is either success or clear error"):
            assert second_start.status_code in (200, 400, 409, 500), (
                f"Unexpected status {second_start.status_code} on double-start. "
                f"Body: {second_start.text}"
            )
            assert second_start.text.strip(), (
                "Empty response body on double-start — silent failure detected"
            )
            body = second_start.json()
            if second_start.status_code == 200:
                assert body.get("recording_id"), "Second start returned 200 but no recording_id"
            else:
                assert "detail" in body, f"Error response missing 'detail': {body}"

        with allure.step("Stop any active recording"):
            client.post(f"/v1/devices/emulator/record/stop/{session_id}", timeout=60.0)

    @allure.id("TC-044")
    @allure.title("Download recording immediately after stop — file is ready without delay")
    @allure.description(
        "Stops a recording and immediately issues a download request without waiting. "
        "Verifies the file is available right away."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    def test_download_immediately_after_stop(
        self, client: httpx.Client, allocated_emulator: dict
    ):
        session_id = allocated_emulator["session_id"]

        with allure.step("Start recording"):
            _start_recording(client, session_id)

        with allure.step(f"Wait {RECORD_DURATION}s to capture content"):
            time.sleep(RECORD_DURATION)

        with allure.step("Stop recording"):
            stop = _stop_recording(client, session_id)
            filename = stop["filename"]

        with allure.step(f"Immediately download {filename} — no wait intentional"):
            response = client.get(
                f"/v1/devices/emulator/record/download/{session_id}/{filename}",
                timeout=120.0,
            )

        with allure.step("Verify file is ready"):
            assert response.status_code == 200, (
                f"File not ready immediately after stop: {response.status_code}. "
                f"Body: {response.text}"
            )
            assert len(response.content) > 0, "Downloaded file is empty immediately after stop"
