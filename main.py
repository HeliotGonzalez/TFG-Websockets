import asyncio
import json
import logging
import contextlib
from urllib.parse import urlparse, parse_qs

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from config import WS_HOST, WS_PORT
from app.connection_manager import manager
from app.redis_listener import start_redis_listener

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(asctime)s %(message)s")

# keep connections alive for at most 30 seconds without activity
IDLE_TIMEOUT = 30


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def extract_path(ws) -> str:
    """
    Return the request path for *all* websockets versions.

    • ≤13.x  -> ws.path
    • ≥14.x  -> ws.request.path
    """
    if hasattr(ws, "path"):
        return ws.path
    if hasattr(ws, "request") and hasattr(ws.request, "path"):
        return ws.request.path
    return ""  # fallback – shouldn't happen

def handshake_get_user_id(path: str) -> int | None:
    """Extract ?user=ID from the URL; return int or None."""
    try:
        qs = parse_qs(urlparse(path).query)
        return int(qs.get("user", [None])[0])
    except Exception:
        return None



async def ws_handler(ws):
    # 1) extract & validate user_id
    user_id = handshake_get_user_id(extract_path(ws))
    if not user_id:
        await ws.close(code=4000, reason="unauthorized")
        return

    # 2) register connection
    await manager.register(user_id, ws)
    logging.info("🔗 Usuario %s conectado", user_id)

    try:
        # initial greeting
        await ws.send(json.dumps({"type": "system", "message": "welcome"}))

        # 3) main receive loop with idle timeout
        while True:
            try:
                # wait for next message, but give up after IDLE_TIMEOUT seconds
                message = await asyncio.wait_for(ws.recv(), timeout=IDLE_TIMEOUT)
            except asyncio.TimeoutError:
                logging.info("🔌 Usuario %s inactivo durante %ds, desconectando", user_id, IDLE_TIMEOUT)
                break
            except (ConnectionClosedOK, ConnectionClosedError):
                # client closed connection normally or due to error
                break
            else:
                # handle the incoming message (if you need to)
                logging.debug("📥 Recibido de %s: %r", user_id, message)
                # … your message-handling logic here …

    except Exception as err:
        logging.error("connection handler failed for %s: %s", user_id, err)

    finally:
        # 4) unregister and clean up
        await manager.unregister(user_id, ws)
        logging.info("❌ Usuario %s desconectado", user_id)

# ----------------------------------------------------------------------
# entry point
# ----------------------------------------------------------------------
async def main():
    redis_task = asyncio.create_task(start_redis_listener())
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        logging.info("🚀 WS server listening on %s:%s", WS_HOST, WS_PORT)
        try:
            await asyncio.Future()
        finally:
            redis_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await redis_task

if __name__ == "__main__":
    asyncio.run(main())
