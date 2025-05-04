"""
User‑accessible grow / teleport commands that forward to your ngrok backend.
Free during an active 'free_grow' event.
"""

import discord, asyncio
from discord import app_commands

from ..utils.io_utils import load_steam_ids, load_balances, save_balances
from ..utils.remote_utils import post_action, backend_available
from ..economy.boosts import is_event_active
from ..utils.logging_utils import log_action
from ..utils.discord_helpers import get_cooldown_time_left, set_cooldown


GROW_COST = 25        # 🐟 cost when no event
CD_SECONDS = 300      # 5‑minute personal cooldown


def setup(client):
    tree = client.tree

    async def _do_remote(inter, endpoint: str):
        if not backend_available():
            return await inter.response.send_message(
                "Sorry, the nest server is offline right now. Try again later.",
                ephemeral=True
            )

        # cooldown
        if (rem := get_cooldown_time_left(inter.user.id, endpoint, CD_SECONDS)):
            m,s = divmod(rem,60)
            return await inter.response.send_message(
                f"Please wait {m}m{s}s before another {endpoint}.",
                ephemeral=True
            )
        set_cooldown(inter.user.id, endpoint)

        user_rec = load_steam_ids().get(str(inter.user.id))
        if not user_rec:
            return await inter.response.send_message(
                "You haven’t linked a Steam ID yet – use /nest first.",
                ephemeral=True
            )

        # charge unless free event
        if endpoint == "grow" and not is_event_active("free_grow"):
            bal = load_balances()
            user_bal = bal.get(str(inter.user.id), {"fish":0,"meat":0})
            if user_bal["fish"] < GROW_COST:
                return await inter.response.send_message(
                    f"Growing costs {GROW_COST} 🐟 – you have {user_bal['fish']}.",
                    ephemeral=True
                )
            user_bal["fish"] -= GROW_COST
            bal[str(inter.user.id)] = user_bal
            save_balances(bal)

        payload = {"steam_id": user_rec["steam_id"], "nickname": user_rec["nickname"]}
        try:
            await post_action(endpoint, payload)
        except Exception as e:
            return await inter.response.send_message(f"Backend error: {e}", ephemeral=True)

        log_action(inter.user.name, inter.user.id, f"/{endpoint}")
        await inter.response.send_message(f"{endpoint.capitalize()} requested – check your game!", ephemeral=True)

    @tree.command(name="grow", description="Grow your animal (costs 25 🐟 unless a free‑grow event)")
    async def grow_cmd(inter: discord.Interaction):
        await _do_remote(inter, "grow")

    @tree.command(name="teleport", description="Teleport your animal to safe spot")
    async def tp_cmd(inter: discord.Interaction):
        await _do_remote(inter, "teleport")

    @tree.command(name="health", description="Show backend connection status")
    async def health_cmd(inter: discord.Interaction):
        status = "online ✅" if backend_available() else "offline ❌"
        await inter.response.send_message(f"Backend is **{status}**.", ephemeral=True)




# Grow

# Teleport

# Weather

# Time










# Announce

# Slay

# Ban, Kick

# Combat Logs