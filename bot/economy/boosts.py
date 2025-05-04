import time
from typing import Dict, Any

# currency boosters kept for compatibility
active_boosts: Dict[str, dict | None] = {"fish": None, "meat": None}

# NEW – arbitrary events, e.g. {"free_grow": {"expires": 1_715_123_456}}
active_events: Dict[str, Dict[str, Any]] = {}

def set_event(name: str, minutes: int, extra: dict | None = None):
    active_events[name] = {"expires": time.time() + minutes * 60, **(extra or {})}

def is_event_active(name: str) -> bool:
    e = active_events.get(name)
    return bool(e and time.time() < e["expires"])
