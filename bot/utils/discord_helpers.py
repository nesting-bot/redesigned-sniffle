"""
Helpers that *need* discord.py types but are still generic utilities.
"""

import time
from typing import List

import discord

from .io_utils import load_command_cooldowns, save_command_cooldowns


def has_any_role(member: discord.Member, names: List[str]) -> bool:
    return any(r.name in names for r in member.roles)


def is_server_booster(member: discord.Member) -> bool:
    return (
        member.premium_since is not None
        or any(r.is_premium_subscriber() or r.name.lower() == "server booster" for r in member.roles)
    )


# ----------------------------------------------------------------------- #
# Cooldown helpers
# ----------------------------------------------------------------------- #
def get_cooldown_time_left(user_id: int, cmd: str, seconds: int) -> int:
    ts = load_command_cooldowns().get(str(user_id), {}).get(cmd)
    if not ts:
        return 0
    rem = seconds - (int(time.time()) - ts)
    return rem if rem > 0 else 0


def set_cooldown(user_id: int, cmd: str) -> None:
    cd = load_command_cooldowns()
    cd.setdefault(str(user_id), {})[cmd] = int(time.time())
    save_command_cooldowns(cd)
