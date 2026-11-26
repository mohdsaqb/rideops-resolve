import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager, suppress

import httpx

INTERVAL_SECONDS = 14 * 60
logger = logging.getLogger(__name__)


async def ping_periodically(url):
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        try:
            async with httpx.AsyncClient(
                timeout=10, follow_redirects=False, trust_env=False
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("Render self-ping failed (%s).", type(exc).__name__)


@asynccontextmanager
async def lifespan(app):
    origin = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    # Render supplies a public HTTPS onrender.com origin for its web services.
    if not re.fullmatch(r"https://[a-z0-9-]+\.onrender\.com", origin, re.IGNORECASE):
        yield
        return
    task = asyncio.create_task(ping_periodically(origin + "/health"))
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
