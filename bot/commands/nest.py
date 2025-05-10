"""
Entrypoint for /nest  – builds on the Views defined in bot.nest.views
"""

import random
import discord
from discord import app_commands
from discord.ext import commands

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
class NestCog(commands.Cog, name="nest"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client = bot            # keep a reference you already use in views

    @app_commands.command(name="nest", description="Begin the Nesting process!")
    async def nest_cmd(self, inter: discord.Interaction):
        # if user already linked a Steam ID, skip straight to code confirm
        linked = load_steam_ids().get(str(inter.user.id))
        if linked:
            parent = NestWorkflowParentView(linked["steam_id"], inter.user.id, self.client)
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
        
async def setup(bot):
    await bot.add_cog(NestCog(bot))
