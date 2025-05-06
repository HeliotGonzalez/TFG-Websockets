# app/events.py
from enum import Enum

class EventType(Enum):
    FRIEND_REQUEST = "friend_request"
    CHAT           = "chat"
