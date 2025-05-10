"""
All sub‑commands under /staff – wired to backend endpoints.

• grow / teleport / weather / time send real payloads.
• /staff announce + currency/event helpers.
• Commands are VISIBLE only to the roles listed in STAFF_ROLE_NAMES.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..bot_config import (
    TEST_GUILD_ID,
    EVENT_CHANNEL_ID,
    PUNISHMENT_LOG_FILE,
    STAFF_ROLE_NAMES,          # set of role *names* allowed to use /staff cmds
)
from ..economy.boosts import active_boosts, set_event
from ..utils.discord_helpers import has_any_role
from ..utils.io_utils import load_balances, load_steam_ids
from ..utils.remote_utils import post_action
from ..utils.logging_utils import log_punishment

# ────────────────────────────────────────────────────────────────────────
#  Decorator helper (runtime check)
# ────────────────────────────────────────────────────────────────────────
def staff_guard(roles: list[str]):
    def decorator(cmd):
        async def predicate(inter: discord.Interaction):
            if has_any_role(inter.user, roles):
                return True
            await inter.response.send_message("❌ You cannot use that command.", ephemeral=True)
            return False

        return app_commands.check(predicate)(cmd)
    return decorator


# ────────────────────────────────────────────────────────────────────────
#  App‑command group (needs to exist before decorators run)
#  default_member_permissions=0 hides the group from everyone
#  — we’ll enable it for staff roles in StaffCog.cog_load().
# ────────────────────────────────────────────────────────────────────────
staff_group = app_commands.Group(
    name="staff",
    description="Staff tools",
    default_member_permissions=discord.Permissions(0),
    dm_permission=False,
)


# ────────────────────────────────────────────────────────────────────────
#  Cog
# ────────────────────────────────────────────────────────────────────────
class StaffCog(commands.Cog, name="staff"):
    """Contains every `/staff …` command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Fast guild‑only registration for dev
        bot.tree.add_command(staff_group, guild=discord.Object(id=TEST_GUILD_ID))

    # ───────────────────────── cog lifecycle ──────────────────────────
    async def cog_load(self):
        """
        Called automatically after the Cog is added & slash‑commands are synced.
        Grants *visibility* of every /staff command to the roles in STAFF_ROLE_NAMES.
        """
        guild = self.bot.get_guild(TEST_GUILD_ID)
        if guild is None:
            return

        allowed_roles = [r for r in guild.roles if r.name in STAFF_ROLE_NAMES]
        if not allowed_roles:
            print("StaffCog: No matching roles – /staff commands stay hidden.")
            return

        perms = [
            app_commands.CommandPermission(
                id=role.id,
                type=app_commands.CommandPermissionType.role,
                permission=True,
            )
            for role in allowed_roles
        ]
        guild_obj = discord.Object(id=TEST_GUILD_ID)
        for cmd in staff_group.walk_commands():
            await self.bot.tree.edit_command_permissions(
                guild=guild_obj,
                command=cmd,
                permissions=perms,
            )
        print(f"StaffCog: bound /staff commands to roles {[r.name for r in allowed_roles]}")

    # ───────────────────────── internal helper ─────────────────────────
    async def _post_and_confirm(
        self,
        inter: discord.Interaction,
        endpoint: str,
        payload: dict,
        success_msg: str,
    ):
        try:
            await post_action(endpoint, payload)
        except Exception as e:                                   # noqa: BLE001
            return await inter.response.send_message(f"Backend error: {e}", ephemeral=True)
        await inter.response.send_message(success_msg, ephemeral=True)

    # ───────────────────────── /staff event ────────────────────────────
    @staff_group.command(name="event", description="Start a currency boost or a server event")
    @staff_guard(["Beta Tester", "Owner"])
    @app_commands.describe(
        event_name="Which event to start",
        boost_type="flat or multiplier (currency only)",
        amount="amount of boost (currency only)",
        duration="duration in minutes",
    )
    @app_commands.choices(
        event_name=[
            app_commands.Choice(name="Fish Boost", value="fish_bonus"),
            app_commands.Choice(name="Meat Boost", value="meat_bonus"),
            app_commands.Choice(name="Free Grow", value="free_grow"),
            app_commands.Choice(name="Free Nest", value="free_nest"),
        ],
        boost_type=[
            app_commands.Choice(name="Flat", value="flat"),
            app_commands.Choice(name="Multiplier", value="multiplier"),
        ],
    )
    async def event_cmd(                    # noqa: PLR0913, C901
        self,
        inter: discord.Interaction,
        event_name: app_commands.Choice[str],
        duration: int,
        boost_type: Optional[app_commands.Choice[str]] = None,
        amount: Optional[int] = None,
    ):
        name = event_name.value

        # Currency boosts -------------------------------------------------
        if name in ("fish_bonus", "meat_bonus"):
            if boost_type is None or amount is None:
                return await inter.response.send_message(
                    "❌ For currency boosts you must specify both `boost_type` and `amount`.",
                    ephemeral=True,
                )
            currency = "fish" if name == "fish_bonus" else "meat"
            flat = amount if boost_type.value == "flat" else 0
            mult = 1 + (amount / 100) if boost_type.value == "multiplier" else 1
            expires = time.time() + duration * 60
            active_boosts[currency] = {"flat": flat, "mult": mult, "expires": expires}

            # Public announcement
            ends_ts = int(expires)
            announcement = (
                f"🎉 A **{currency.capitalize()}** boost is live! "
                f"{'+'+str(amount)+'%' if boost_type.value=='multiplier' else '+'+str(amount)} "
                f"{currency} for {duration} minutes. Ends <t:{ends_ts}:R>."
            )
            await inter.client.get_channel(EVENT_CHANNEL_ID).send(announcement)
            return await inter.response.send_message("✅ Currency boost applied.", ephemeral=True)

        # Timed events ----------------------------------------------------
        if name in ("free_grow", "free_nest"):
            set_event(name, duration)
            return await inter.response.send_message(
                f"✅ Event **{name}** started for {duration} minutes.", ephemeral=True
            )

        await inter.response.send_message("❌ Unknown event.", ephemeral=True)

    # ─────────────────────── /staff balance ────────────────────────────
    @staff_group.command(name="balance", description="Check a player's balance")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_balance(self, inter: discord.Interaction, member: discord.Member):
        bal = load_balances().get(str(member.id), {"fish": 0, "meat": 0})
        await inter.response.send_message(
            f"{member.display_name} has {bal['fish']} 🐟 and {bal['meat']} 🥩", ephemeral=True
        )

    # ─────────────────────── /staff steamid ────────────────────────────
    @staff_group.command(name="steamid", description="Show user's Steam ID")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_steamid(self, inter: discord.Interaction, member: discord.Member):
        sid = load_steam_ids().get(str(member.id))
        await inter.response.send_message(
            f"{member.display_name}'s Steam ID: `{sid or 'None linked'}`", ephemeral=True
        )

    # ─────────────────── grow / teleport / weather / time ──────────────
    @staff_group.command(name="grow", description="Grow a player (ignores cost)")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_grow(self, inter: discord.Interaction, member: discord.Member):
        rec = load_steam_ids().get(str(member.id))
        if rec is None:
            return await inter.response.send_message(
                f"{member.display_name} has no linked Steam ID.", ephemeral=True
            )
        await self._post_and_confirm(
            inter,
            "grow",
            {"steam_id": rec["steam_id"], "nickname": rec["nickname"]},
            f"{member.display_name} is being grown!",
        )

    @staff_group.command(name="teleport", description="Teleport a player")
    @staff_guard(["Mod", "Admin", "Event Planner", "Head Admin", "Beta Tester", "Owner"])
    async def staff_teleport(self, inter: discord.Interaction, member: discord.Member):
        rec = load_steam_ids().get(str(member.id))
        if rec is None:
            return await inter.response.send_message(
                f"{member.display_name} has no linked Steam ID.", ephemeral=True
            )
        await self._post_and_confirm(
            inter,
            "teleport",
            {"steam_id": rec["steam_id"], "nickname": rec["nickname"]},
            f"{member.display_name} has been teleported!",
        )

    @staff_group.command(name="weather", description="Set weather (ignores cooldown)")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_weather(self, inter: discord.Interaction, pattern: str):
        await self._post_and_confirm(
            inter, "weather", {"pattern": pattern}, f"Weather changed to **{pattern}**!"
        )

        # auto‑revert after 13–20 min
        delay = random.randint(13 * 60, 20 * 60)

        async def _revert():                              # noqa: WPS430
            await asyncio.sleep(delay)
            try:
                await post_action("weather", {"pattern": "sun"})
            except Exception:
                pass

        asyncio.create_task(_revert())

    @staff_group.command(name="time", description="Set in‑game time (ignores cooldown)")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_time(self, inter: discord.Interaction, ticks: int):
        await self._post_and_confirm(
            inter, "time", {"ticks": ticks}, f"Time has been set to **{ticks}** ticks."
        )

    # ───────────────────────── /staff announce ─────────────────────────
    @staff_group.command(name="announce", description="Send announcement (255 chars)")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_announce(self, inter: discord.Interaction, message: str):
        if len(message) > 255:
            return await inter.response.send_message(
                "❌ Announcement exceeds 255 characters.", ephemeral=True
            )
        await self._post_and_confirm(
            inter, "announce", {"message": message}, "Announcement broadcast!"
        )

    # ─────────────────────── logs / punishments ────────────────────────
    @staff_group.command(name="logs", description="Get punishment log")
    @staff_guard(["Beta Tester", "Owner", "Admin", "Head Admin"])
    async def staff_logs(self, inter: discord.Interaction, log_type: str):
        if log_type.lower() != "admin":
            return await inter.response.send_message("Kill logs WIP.", ephemeral=True)
        await inter.response.send_message(
            "Admin log:",
            file=discord.File(PUNISHMENT_LOG_FILE, filename="punishment_log.txt"),
            ephemeral=True,
        )

    @staff_group.command(name="ban", description="Log a permanent ban")
    @staff_guard(["Admin"])
    async def staff_ban(self, inter: discord.Interaction, member: discord.Member, reason: str):
        log_punishment("BAN", member, reason, inter.user)
        await inter.response.send_message(
            f"{member.display_name} has been **PERMANENTLY** banned for '{reason}'.", ephemeral=True
        )

    @staff_group.command(name="mute", description="Temporarily mute a player")
    @staff_guard(["Moderator", "Admin"])
    async def staff_mute(
        self,
        inter: discord.Interaction,
        member: discord.Member,
        duration: int,
        reason: Optional[str] = None,
    ):
        log_punishment("MUTE", member, reason or "no reason", inter.user)
        await inter.response.send_message(
            f"🔇 {member.display_name} muted for {duration} minutes.", ephemeral=True
        )

    @staff_group.command(name="kick", description="Kick a player")
    @staff_guard(
        ["Trial Staff", "Mod", "Admin", "Event Planner", "Head Admin", "Beta Tester", "Owner"]
    )
    async def staff_kick(self, inter: discord.Interaction, member: discord.Member, reason: str):
        await inter.response.send_message(
            f"{member.display_name} has been kicked for {reason}!", ephemeral=True
        )

    @staff_group.command(name="warn", description="Warn a player")
    @staff_guard(
        ["Trial Staff", "Mod", "Admin", "Event Planner", "Head Admin", "Beta Tester", "Owner"]
    )
    async def staff_warn(self, inter: discord.Interaction, member: discord.Member, reason: str):
        await inter.response.send_message(
            f"{member.display_name} has been warned for {reason}!", ephemeral=True
        )


# ───────────────────────── extension entry‑point ────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(StaffCog(bot))
