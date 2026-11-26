import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app import keepalive
from app.main import app


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "",
        "http://localhost:3000",
        "https://127.0.0.1",
        "https://[::1]",
        "https://app.onrender.com@localhost",
    ],
)
def test_health_without_ping(origin, monkeypatch):
    if origin is None:
        monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    else:
        monkeypatch.setenv("RENDER_EXTERNAL_URL", origin)
    ping = AsyncMock()
    monkeypatch.setattr(keepalive, "ping_periodically", ping)
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200 and response.json() == {"status": "ok"}
    ping.assert_not_called()


def test_render_ping_repeats_after_failure_and_stops(monkeypatch):
    url = "https://rideops-resolve.onrender.com"
    monkeypatch.setenv("RENDER_EXTERNAL_URL", url + "/")
    requests = []

    async def get(client, target):
        requests.append(target)
        if len(requests) == 1:
            raise httpx.ConnectError("temporarily unavailable")
        return httpx.Response(200, request=httpx.Request("GET", target))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)

    async def run():
        intervals = []
        waiting = asyncio.Event()

        async def sleep(seconds):
            intervals.append(seconds)
            if len(intervals) == 3:
                waiting.set()
                await asyncio.Event().wait()

        monkeypatch.setattr(keepalive.asyncio, "sleep", sleep)
        async with keepalive.lifespan(app):
            await asyncio.wait_for(waiting.wait(), timeout=1)
        assert intervals == [840, 840, 840]
        assert requests == [url + "/health"] * 2

    asyncio.run(run())
