"""
Lightweight JSON on‑disk helpers + strongly‑typed loader/ saver shortcuts.
"""

import json
from typing import Any, Dict

from ..bot_config import (
    BALANCES_FILE,
    COOLDOWNS_FILE,
    MESSAGES_FILE,
    STEAM_IDS_FILE,
)

# ----------------------------------------------------------------------- #
# Generic helpers
# ----------------------------------------------------------------------- #
def _json_load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _json_save(path, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)





# ----------------------------------------------------------------------- #
# Specific typed helpers (one‑liners via lambdas so call‑site is tiny)
# ----------------------------------------------------------------------- #
load_balances          = lambda: _json_load(BALANCES_FILE, {})
save_balances          = lambda d: _json_save(BALANCES_FILE, d)

load_command_cooldowns = lambda: _json_load(COOLDOWNS_FILE, {})
save_command_cooldowns = lambda d: _json_save(COOLDOWNS_FILE, d)

load_messages          = lambda: _json_load(MESSAGES_FILE, {})
load_steam_ids         = lambda: _json_load(STEAM_IDS_FILE, {})
save_steam_ids         = lambda d: _json_save(STEAM_IDS_FILE, d)
