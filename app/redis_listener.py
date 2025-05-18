# app/redis_listener.py
import asyncio
import json
import logging
import re
import contextlib
import redis.asyncio as aioredis

from .connection_manager import manager
from .events import EventType
from config import REDIS_URL

log = logging.getLogger(__name__)

CHANNELS = {
    "friend-request": EventType.FRIEND_REQUEST,
    "chat":           EventType.CHAT,
    "friend-accepted": EventType.FRIEND_ACCEPTED,
}

def normalize_to_json(raw: str) -> str:
    """
    Convierte {key:val, ...} en JSON válido:
     - Añade comillas a las claves
     - Añade comillas a valores de texto no numéricos
    """
    s = raw.strip()
    # 1) claves sin comillas → "clave":
    s = re.sub(r'([{\s,])([A-Za-z_]\w*)\s*:', r'\1"\2":', s)
    # 2) valores de texto (que no empiecen por dígito, [, {, "]) → "valor"
    def _quote_val(match):
        val = match.group(1).strip()
        return f':"{val}"'
    s = re.sub(r':\s*([^,"\[\]\{\}\d][^,\}\]]*)', _quote_val, s)
    return s

async def start_redis_listener():
    """Escucha Redis de forma resiliente, con reconexión infinita."""
    while True:
        client = pubsub = None
        try:
            client = aioredis.from_url(
                REDIS_URL,
                decode_responses=True
            )
            pubsub = client.pubsub()
            await pubsub.subscribe(*CHANNELS.keys())
            log.info("🔔 Suscrito a Redis: %s", ", ".join(CHANNELS.keys()))

            async for msg in pubsub.listen():
                if msg.get("type") != "message":
                    continue

                raw = msg["data"]
                # intentamos JSON directo...
                log.info("🔔 RAW Redis en '%s': %r", msg["channel"], raw)
                try:
                    data = json.loads(raw)
                except (json.JSONDecodeError, TypeError) as e:
                    log.error("JSON malformado en canal %s: %s – %r", msg["channel"], e, raw)
                    continue
                else:
                    log.info("✅ JSON parseado correctamente: %s", data)

                event_type = CHANNELS.get(msg["channel"])
                if event_type:
                    await manager.broadcast(event_type, data)

        except asyncio.CancelledError:
            log.info("❎ Redis listener cancelado, cerrando conexión...")
            raise

        except Exception as exc:
            log.exception("Redis listener falló – reintento en 5 s: %s", exc)

        finally:
            # limpieza siempre antes de reintentar o salir
            if pubsub:
                with contextlib.suppress(Exception):
                    await pubsub.reset()
            if client:
                with contextlib.suppress(Exception):
                    await client.close()
            await asyncio.sleep(5)
