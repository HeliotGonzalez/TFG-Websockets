# app/redis_listener.py
import asyncio
import json
import logging
import redis.asyncio as aioredis

from .connection_manager import manager
from .events import EventType
from config import REDIS_URL

log = logging.getLogger(__name__)

CHANNELS = {
    "friend-request": EventType.FRIEND_REQUEST,
    "chat"          : EventType.CHAT,
}

# app/redis_listener.py
async def start_redis_listener():
    while True:
        try:
            client = aioredis.from_url(REDIS_URL, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(*CHANNELS.keys())
            log.info("🔔 Suscrito a Redis: %s", ", ".join(CHANNELS.keys()))

            async for msg in pubsub.listen():
                if msg["type"] != "message":
                    continue
                data = json.loads(msg["data"])
                event_type = CHANNELS.get(msg["channel"])
                if event_type:
                    await manager.broadcast(event_type, data)

        except Exception as exc:
            log.exception("Redis listener failed, retrying in 5 s: %s", exc)
            await asyncio.sleep(5)      # espera y reintenta

