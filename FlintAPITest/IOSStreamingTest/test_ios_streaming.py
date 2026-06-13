from playwright.sync_api import sync_playwright
import os
import requests

API_BASE = os.getenv("FLINT_API_BASE")
TOKEN = os.getenv("TOKEN")


def launch_browser(p):
    return p.chromium.launch(
        channel="chrome",
        headless=True
    )


def wait_for_stream(page):

    page.wait_for_function(
        """
        () => {
            const video =
                document.querySelector("video");

            return (
                video &&
                video.srcObject &&
                video.currentTime > 0
            );
        }
        """,
        timeout=120000
    )


def stream_is_active(page):

    return page.evaluate(
        """
        () => {
            const video =
                document.querySelector("video");

            return (
                video &&
                video.srcObject &&
                video.currentTime > 0
            );
        }
        """
    )


def test_stream_launch(streaming_url):

    with sync_playwright() as p:

        browser = launch_browser(p)

        try:

            page = browser.new_page()

            page.goto(streaming_url)

            wait_for_stream(page)

            assert stream_is_active(page)

        finally:

            browser.close()


def test_refresh_recovery(streaming_url):

    with sync_playwright() as p:

        browser = launch_browser(p)

        try:

            page = browser.new_page()

            page.goto(streaming_url)

            wait_for_stream(page)

            page.reload()

            wait_for_stream(page)

            assert stream_is_active(page)

        finally:

            browser.close()


def test_multiple_tabs(streaming_url):

    with sync_playwright() as p:

        browser = launch_browser(p)

        try:

            page1 = browser.new_page()
            page2 = browser.new_page()

            page1.goto(streaming_url)
            page2.goto(streaming_url)

            wait_for_stream(page1)
            wait_for_stream(page2)

            assert stream_is_active(page1)
            assert stream_is_active(page2)

        finally:

            browser.close()


def test_invalid_stream_token(streaming_url):

    bad_url = streaming_url[:-5] + "ABCDE"

    with sync_playwright() as p:

        browser = launch_browser(p)

        try:

            page = browser.new_page()

            page.goto(bad_url)

            page.wait_for_timeout(10000)

            html = page.content().lower()

            assert (
                "invalid" in html
                or "expired" in html
                or "unable to start stream" in html
            )

        finally:

            browser.close()


def release_device(device_id):

    response = requests.post(
        f"{API_BASE}/v1/devices/physical/release/{device_id}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
        },
        timeout=30,
    )

    response.raise_for_status()



def test_stream_stops_after_release(
    streaming_url,
    session_data
):

    device_id = session_data["device_details"]["id"]

    with sync_playwright() as p:

        browser = launch_browser(p)

        try:

            page = browser.new_page()

            page.goto(streaming_url)

            wait_for_stream(page)

            before = page.evaluate(
                """
                () => {
                    const v =
                        document.querySelector("video");
                    return v.currentTime;
                }
                """
            )

            release_device(device_id)

            page.wait_for_timeout(15000)

            after = page.evaluate(
                """
                () => {
                    const v =
                        document.querySelector("video");
                    return v.currentTime;
                }
                """
            )

            print(
                f"Before={before}, After={after}"
            )

            assert after == before

        finally:

            browser.close()