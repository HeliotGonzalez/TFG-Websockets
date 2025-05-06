import json
from collections import defaultdict
from .events import EventType

class ConnectionManager:
    def __init__(self):
        # { user_id: set([WebSocketConnection, ...]) }
        self.clients = defaultdict(set)

    async def register(self, user_id: int, ws):
        self.clients[user_id].add(ws)

    async def unregister(self, user_id: int, ws):
        self.clients[user_id].discard(ws)
        if not self.clients[user_id]:
            del self.clients[user_id]

    async def broadcast(self, event_type: EventType, data: dict):
        to_user = data.get("to")
        if not to_user:
            return

        payload = {"type": event_type.value, **data}
        for ws in list(self.clients.get(to_user, [])):
            try:
                await ws.send(json.dumps(payload))
            except Exception:
                pass   # could call unregister here

manager = ConnectionManager()
