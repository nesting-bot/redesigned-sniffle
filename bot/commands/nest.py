"""
Entrypoint for /nest  – builds on the Views defined in bot.nest.views
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
    LinkSteamView,
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
                "‌‌ \n"
                "**Welcome to the Nesting Channel**\n\n"
                "Do you have a code from the CenoColors website?",
                view=parent,
            )
            return
        else: 
            await inter.response.send_message(
                "‌‌ \n"
                "You haven't linked your Steam ID yet. Would you like to link now?\n\n"
                "Linking your Steam ID allows YOUR account to receive a nest\n"
                "and ensures only you can create animals on your Steam account.",
                view=LinkSteamView(),
                ephemeral=True
            )
            return