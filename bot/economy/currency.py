import random

import discord

from ..utils.discord_helpers import is_server_booster, has_any_role
from .boosts import apply_boost


def calc_fish(member: discord.Member) -> int:
    low, high = 2, 5
    if is_server_booster(member):
        low += 1
    if has_any_role(member, ["Complete Achievements"]):
        high += 1
    if has_any_role(member, ["Legendary Beast"]):
        high += 3
    return apply_boost("fish", random.randint(low, high))


def calc_meat(member: discord.Member) -> int:
    low, high = 1, 1
    if is_server_booster(member):
        high += 1
    if has_any_role(member, ["Complete Achievements"]):
        high += 1
    if has_any_role(member, ["Legendary Beast"]):
        high += 2
    return apply_boost("meat", random.randint(low, high))
