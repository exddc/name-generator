"""Server-sent event utilities shared by streaming endpoints."""

import asyncio
import datetime
import json
from collections.abc import AsyncIterator

SSE_RESPONSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
}


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def with_heartbeat(
    source: AsyncIterator[str], interval_seconds: float
) -> AsyncIterator[str]:
    """Forward a stream and emit heartbeat events while its producer is idle."""
    iterator = source.__aiter__()
    pending = asyncio.create_task(anext(iterator))
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=interval_seconds)
            if not done:
                yield format_sse(
                    "heartbeat",
                    {"timestamp": datetime.datetime.now(datetime.UTC).isoformat()},
                )
                continue

            try:
                item = pending.result()
            except StopAsyncIteration:
                break

            yield item
            pending = asyncio.create_task(anext(iterator))
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        close = getattr(iterator, "aclose", None)
        if close is not None:
            await close()
