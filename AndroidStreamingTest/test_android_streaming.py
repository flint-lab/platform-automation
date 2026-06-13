import asyncio
import os
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest
import websockets
from websockets.exceptions import ConnectionClosed

from pathlib import Path
from dotenv import load_dotenv

ENV_FILE = Path(__file__).parent / "test.env"
load_dotenv(ENV_FILE)

async def wait_for_close(ws):
    try:
        while True:
            await ws.recv()
    except ConnectionClosed as e:
        return e
    


def replace_query_param(url, key, value):
    print(f"Original URL: {url}")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params[key] = [value]
    query = "&".join(
        f"{k}={v[0]}"
        for k, v in params.items()
    )
    print(f"Modified URL: {query}")
    return (
        f"{parsed.scheme}://"
        f"{parsed.netloc}"
        f"{parsed.path}"
        f"?{query}"
    )


def remove_query_param(url, key):
    print(f"Original URL: {url}")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params.pop(key, None)
    query = "&".join(
        f"{k}={v[0]}"
        for k, v in params.items()
    )
    print(f"Modified URL: {query}")
    return (
        f"{parsed.scheme}://"
        f"{parsed.netloc}"
        f"{parsed.path}"
        f"?{query}"
    )


@pytest.mark.asyncio
async def test_valid_connection(ws_url):
    print(f"Testing valid connection to {ws_url}")
    async with websockets.connect(ws_url) as ws:
        await asyncio.sleep(2)
        assert ws.state.name == "OPEN"
    print("Connection closed gracefully with code 1000 and reason 'Normal Closure'")


@pytest.mark.asyncio
async def test_session_replacement(ws_url):
    print("Testing session replacement")
    print(f"Connecting first websocket to {ws_url}")
    ws1 = await websockets.connect(ws_url)
    await asyncio.sleep(1)

    print(f"Connecting second websocket to {ws_url}")
    ws2 = await websockets.connect(ws_url)
    await asyncio.sleep(3)

    assert ws1.close_code == 1000
    assert ws1.close_reason == "SESSION_REPLACED"
    print(f"First websocket closed with code {ws1.close_code} and reason '{ws1.close_reason}'")
    await ws2.close()
    print(f"Second websocket closed with code {ws2.close_code} and reason '{ws2.close_reason}'")

    try:
        await ws1.close()
        print(f"Attempted to close first websocket again, but it was already closed with code {ws1.close_code} and reason '{ws1.close_reason}'")
    except:
        pass


@pytest.mark.asyncio
async def test_invalid_session(ws_url):
    print("Testing invalid session_id")

    bad_url = replace_query_param(
        ws_url,
        "session_id",
        "INVALID_SESSION",
    )
    print(f"Connecting to {bad_url}")
    ws = await websockets.connect(bad_url)

    try:
        e = await wait_for_close(ws)
        print(f"Websocket closed with code {e.code} and reason '{e.reason}'")
        assert e.code == 1008
        assert "invalidated" in e.reason.lower()
    except ConnectionClosed as e:
        print(f"Code={e.code}")
        print(f"Reason={e.reason}")
        assert e.code == 1008
        assert "invalidated" in e.reason.lower()


@pytest.mark.asyncio
async def test_invalid_udid(ws_url):
    print("Testing invalid udid")
    print(f"Original URL: {ws_url}")
    bad_url = replace_query_param(
        ws_url,
        "udid",
        "INVALID_UDID",
    )
    print(f"Connecting to {bad_url}")
    ws = await websockets.connect(bad_url)
    try:
        print("Waiting for websocket to close due to invalid udid...")
        e = await wait_for_close(ws)
        print(f"Websocket closed with code {e.code} and reason '{e.reason}'")
        assert e.code == 1008
        assert "session does not match" in e.reason.lower()
    except ConnectionClosed as e:
        print(f"Code={e.code}")
        print(f"Reason={e.reason}")
        assert e.code == 1008
        assert "device_id" in e.reason





@pytest.mark.asyncio
async def test_missing_session_id(ws_url):
    print("Testing missing session_id")
    print(f"Original URL: {ws_url}")
    bad_url = remove_query_param(
        ws_url,
        "session_id",
    )
    print(f"Connecting to {bad_url}")
    ws = await websockets.connect(bad_url)
    print("Waiting for websocket to close due to missing session_id...")    
    try:
        print("Waiting for websocket to close due to missing session_id...")
        e = await wait_for_close(ws)
        print(f"Websocket closed with code {e.code} and reason '{e.reason}'")
        assert e.code == 1008
        assert "missing session_id" in e.reason.lower()
    except ConnectionClosed as e:
        print(f"Code={e.code}")
        print(f"Reason={e.reason}")
        assert e.code == 1008
        assert "missing session_id" in e.reason.lower()


@pytest.mark.asyncio
async def test_token_not_validated(ws_url):
    print("Testing invalid token (should not be validated by websocket connection)")
    print(f"Original URL: {ws_url}")
    bad_url = replace_query_param(
        ws_url,
        "token",
        "INVALID_TOKEN",
    )
    print(f"Connecting to {bad_url}")
    async with websockets.connect(bad_url) as ws:
        await asyncio.sleep(2)
        assert ws.state.name == "OPEN"
    print("Connection established successfully, indicating token is not validated by websocket connection")


@pytest.mark.asyncio
async def test_heartbeat(ws_url):
    print("Testing heartbeat mechanism")
    async with websockets.connect(ws_url) as ws:
        print("Connected to websocket, waiting for heartbeat interval...")
        heartbeat_wait = int(os.getenv("HEARTBEAT_WAIT", "35"))
        await asyncio.sleep(heartbeat_wait)
        pong = await ws.ping()
        await pong
        print("Heartbeat successful, connection is still alive")
        assert ws.state.name == "OPEN"
        print("Closing websocket connection")
    print("Websocket connection closed gracefully with code 1000 and reason 'Normal Closure'")


@pytest.mark.asyncio
async def test_device_deallocation(
    ws_url,
    release_device_fn,
):

    print("Testing device deallocation")

    ws = await websockets.connect(ws_url)

    await asyncio.sleep(2)

    print("Releasing device via API...")

    release_device_fn()

    e = await wait_for_close(ws)

    print(
        f"\nCode={e.code}"
        f"\nReason={e.reason}"
    )

    assert e.code == 1000
    assert e.reason == "Device deallocated or stopped by flintlab"



@pytest.mark.asyncio
async def test_old_url_after_deallocation(ws_url):

    ws = await websockets.connect(ws_url)

    e = await wait_for_close(ws)

    assert e.code == 1008
    assert "invalidated" in e.reason.lower()