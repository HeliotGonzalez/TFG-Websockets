# app/events.py
from enum import Enum

class EventType(Enum):
    FRIEND_REQUEST = "friend_request"
    CHAT           = "chat"
    FRIEND_ACCEPTED = "friend-accepted"
    FRIEND_DENIED = "friend-denied"
    VIDEO_CORRECTED = "video-corrected"
    
