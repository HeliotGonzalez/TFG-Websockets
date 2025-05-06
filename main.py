import asyncio
import json
import logging
from urllib.parse import urlparse, parse_qs

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from config import WS_HOST, WS_PORT
from app.connection_manager import manager
from app.redis_listener import start_redis_listener

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s %(asctime)s %(message)s")

# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def extract_path(ws) -> str:
    """
    Return the request path for *all* websockets versions.

    • ≤13.x  -> ws.path
    • ≥14.x  -> ws.request.path
    """
    if hasattr(ws, "path"):                       # ≤ 13.x:contentReference[oaicite:3]{index=3}
        return ws.path
    if hasattr(ws, "request") and hasattr(ws.request, "path"):  # ≥ 14.0:contentReference[oaicite:4]{index=4}
        return ws.request.path
    return ""  # fallback – shouldn't happen

def handshake_get_user_id(path: str) -> int | None:
    """Extract ?user=ID from the URL; return int or None."""
    try:
        qs = parse_qs(urlparse(path).query)
        return int(qs.get("user", [None])[0])
    except Exception:
        return None

# ----------------------------------------------------------------------
# WebSocket handler (NEW signature: one argument)
# ----------------------------------------------------------------------
async def ws_handler(ws):
    # 1) basic token in query string
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

        # 3) keep the socket open until the client closes it
        async for _ in ws:
            pass

    except (ConnectionClosedOK, ConnectionClosedError):
        pass
    except Exception as err:
        logging.error("connection handler failed: %s", err)

    finally:
        # 4) unregister
        await manager.unregister(user_id, ws)
        logging.info("❌ Usuario %s desconectado", user_id)

# ----------------------------------------------------------------------
# entry point
# ----------------------------------------------------------------------
async def main():
    asyncio.create_task(start_redis_listener())        # Redis listener
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        logging.info("🚀 WS server listening on %s:%s", WS_HOST, WS_PORT)
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
