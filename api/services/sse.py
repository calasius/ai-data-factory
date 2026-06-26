import asyncio
import json
from collections import defaultdict
from typing import AsyncGenerator

_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


async def subscribe(channel: str) -> AsyncGenerator[str, None]:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers[channel].append(q)
    try:
        # Initial ping so the client knows the channel is open
        yield ": connected\n\n"
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=15.0)
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat to keep the connection alive through proxies
                yield ": ping\n\n"
    finally:
        try:
            _subscribers[channel].remove(q)
        except ValueError:
            pass


async def publish(channel: str, event: dict) -> None:
    dead = []
    for q in list(_subscribers[channel]):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            _subscribers[channel].remove(q)
        except ValueError:
            pass


async def close_channel(channel: str) -> None:
    for q in list(_subscribers[channel]):
        try:
            q.put_nowait(None)
        except asyncio.QueueFull:
            pass
