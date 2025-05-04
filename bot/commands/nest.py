"""
Entrypoint for /nest  – builds on the Views defined in bot.nest.views
"""

import random
import discord
from discord import app_commands

from ..utils.io_utils import load_steam_ids, save_steam_ids
from ..utils.logging_utils import log_action
from ..utils.discord_helpers import has_any_role
from ..bot_config import TEST_GUILD_ID
from ..nest.views import (
    extract_17digit_id,
    NestWorkflowParentView,
    SteamIdModal,
)

# ----------------------------------------------------------------------- #
def setup(client) -> None:
    tree = client.tree

    @tree.command(name="nest", description="Begin the Nesting process!")
    async def nest_cmd(inter: discord.Interaction):
        # if user already linked a Steam ID, skip straight to code confirm
        linked = load_steam_ids().get(str(inter.user.id))
        if linked:
            parent = NestWorkflowParentView(linked["steam_id"], inter.user.id, client)
            # include nickname in prompt
            await inter.response.send_message(
                f"Ready to nest for **{linked['nickname']}** (Steam ID `{linked['steam_id']}`)?",
                view=parent,
                ephemeral=True,
            )
            return
        else: 
            await inter.response.send_message(
                "First time using /nest? You'll need to link your 17‑digit Steam ID.",
                view=SteamIdModal(),
                ephemeral=True,
            )
            return