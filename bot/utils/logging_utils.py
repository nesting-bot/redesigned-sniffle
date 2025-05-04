"""
Small helpers that append log lines to plain‑text files.
"""

import time
from ..bot_config import LOG_FILE, PUNISHMENT_LOG_FILE


def log_action(username: str, user_id: int, command: str) -> None:
    ts = int(time.time())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] USERNAME={username} USER_ID={user_id} COMMAND={command}\n")


def log_punishment(action: str, member, reason: str, staff) -> None:
    ts = int(time.time())
    with open(PUNISHMENT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {staff} -> {member} : {action} : {reason}\n")
