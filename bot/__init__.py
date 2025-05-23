"""
Initialises the Discord client, registers every command package and exposes
`run_bot()` that the tiny bootstrap file calls.
"""

import discord
from discord.ext import commands
from discord import app_commands

from .bot_config import DISCORD_TOKEN, TEST_GUILD_ID
from .utils.colorpack import load_colorpacks_reverse, load_colorpack_meta
from .utils.remote_utils import background_health_probe, set_backend_status

# -------- import command modules so their `setup()` functions are available
from .commands import currency, staff, game, nest  # noqa: F401 (import side effects)


class CenoClient(commands.Bot):
    """
    Thin wrapper that owns the CommandTree & colour‑pack maps.
    """
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)   # prefix unused, but required

        # self.tree already exists on commands.Bot
        # cached colour‑pack look‑ups
        self.colorpacks_map = load_colorpacks_reverse()
        self.pack_permissions = load_colorpack_meta()

    # ------------------------------------------------------------------ #
    # discord.py lifecycle
    # ------------------------------------------------------------------ #
    async def setup_hook(self) -> None:
        """
        Register slash commands *per guild* (fast) while developing.
        Switch to `self.tree.sync()` for global deploys.
        """
        guild = discord.Object(id=TEST_GUILD_ID)

        # Each commands.<name>.setup(...) attaches its commands to the tree
        for ext in ("bot.commands.currency",
                    "bot.commands.staff",
                    "bot.commands.game",
                    "bot.commands.nest"):
            await self.load_extension(ext)
            print(f"Loaded {ext}")

        await self.tree.sync(guild=guild)
        print("Slash‑commands synced to test guild.")


        # ------------------- backend health‑probe -------------------- #
        self.loop.create_task(background_health_probe(self))
        # mark “unknown” until first probe returns
        set_backend_status(False)


# single shared instance
client = CenoClient()


def run_bot() -> None:
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN missing – add it to your .env file")
    client.run(DISCORD_TOKEN)
