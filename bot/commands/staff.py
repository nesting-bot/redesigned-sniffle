"""
All sub‑commands under /staff
"""

import time
from typing import Optional

import discord
from discord import app_commands

from ..economy.boosts import active_boosts, set_event
from ..utils.discord_helpers import has_any_role
from ..utils.io_utils import (
    load_balances,
    load_steam_ids,
)
from ..utils.logging_utils import log_punishment
from ..bot_config import TEST_GUILD_ID, EVENT_CHANNEL_ID, PUNISHMENT_LOG_FILE


# ----------------------------------------------------------------------- #
# Decorator helper: wraps app_commands.check
# ----------------------------------------------------------------------- #
def staff_guard(names: list[str]):
    def decorator(func):
        async def predicate(inter: discord.Interaction):
            if has_any_role(inter.user, names):
                return True
            await inter.response.send_message("❌ You cannot use that command.", ephemeral=True)
            return False

        return app_commands.check(predicate)(func)
    return decorator

def log_punishment(action: str, member: discord.Member, reason: str, staff: discord.Member):
    ts = int(time.time())
    with open(PUNISHMENT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {staff} -> {member} : {action} : {reason}\n")

# ----------------------------------------------------------------------- #
# Registration API
# ----------------------------------------------------------------------- #
def setup(client) -> None:
    tree = client.tree
    staff_group = app_commands.Group(name="staff", description="Staff tools")
    tree.add_command(staff_group, guild=discord.Object(id=TEST_GUILD_ID))


    # ------------------------------------------------------------------- #
    # /staff event → unified boost + other events
    # ------------------------------------------------------------------- #
    @staff_group.command(
        name="event",
        description="Start a currency boost or a server event"
    )
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
    async def event_cmd(
        inter: discord.Interaction,
        event_name: app_commands.Choice[str],
        duration: int,
        boost_type: Optional[app_commands.Choice[str]] = None,
        amount: Optional[int] = None,
    ):
        name = event_name.value

        # Currency boosts
        if name in ("fish_bonus", "meat_bonus"):
            if boost_type is None or amount is None:
                return await inter.response.send_message(
                    "❌ For currency boosts you must specify both `boost_type` and `amount`.",
                    ephemeral=True
                )

            currency = "fish" if name == "fish_bonus" else "meat"
            flat = amount if boost_type.value == "flat" else 0
            mult = 1 + (amount / 100) if boost_type.value == "multiplier" else 1
            expires = time.time() + duration * 60

            active_boosts[currency] = {
                "flat":  flat,
                "mult":  mult,
                "expires": expires,
            }

            # Public announcement in your event channel
            ends_ts = int(expires)
            announcement = (
                f"🎉 A **{currency.capitalize()}** boost is live! "
                f"{'+'+str(amount)+'%' if boost_type.value=='multiplier' else '+'+str(amount)} "
                f"{currency} for {duration} minutes. Ends <t:{ends_ts}:R>."
            )
            await inter.client.get_channel(EVENT_CHANNEL_ID).send(announcement)

            return await inter.response.send_message("✅ Currency boost applied.", ephemeral=True)


        # Other timed events
        if name in ("free_grow", "free_nest"):
            set_event(name, duration)
            return await inter.response.send_message(
                f"✅ Event **{name}** started for {duration} minutes.",
                ephemeral=True
            )

        # Fallback
        await inter.response.send_message("❌ Unknown event.", ephemeral=True)


    # ------------------------ /staff balance (player) --------------------------- #
    @staff_group.command(name="balance", description="Check a player's balance")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_balance(inter: discord.Interaction, member: discord.Member):
        bal = load_balances().get(str(member.id), {"fish": 0, "meat": 0})
        await inter.response.send_message(
            f"{member.display_name} has {bal['fish']} 🐟 and {bal['meat']} 🥩",
            ephemeral=True,
        )


    # ------------------------ /staff steamid (player) -------------------------- #
    @staff_group.command(name="steamid", description="Show user's Steam ID")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_steamid(inter: discord.Interaction, member: discord.Member):
        sid = load_steam_ids().get(str(member.id))
        await inter.response.send_message(
            f"{member.display_name}'s Steam ID: `{sid or 'None linked'}`",
            ephemeral=True
        )


    # ------------------------------------------------------------------ #
    # remaining staff sub‑commands
    # ------------------------------------------------------------------ #
    @staff_group.command(name="logs", description="Get punishment log")
    @staff_guard(["Beta Tester", "Owner", "Admin", "Head Admin"])
    async def staff_logs(inter: discord.Interaction, log_type: str):
        if log_type.lower() != "admin":
            return await inter.response.send_message("Kill logs WIP.", ephemeral=True)
        await inter.response.send_message(
            "Admin log:",
            file=discord.File(PUNISHMENT_LOG_FILE, filename="punishment_log.txt"),
            ephemeral=True
        )


    @staff_group.command(name="grow", description="Grow a player")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_grow(
        inter: discord.Interaction,
        member: discord.Member,
        stage: app_commands.Choice[str]
    ):
        await inter.response.send_message(
            f"{member.display_name} has been grown to a {stage.value} adult!",
            ephemeral=True
        )


    @staff_group.command(name="time", description="Set in‑game time")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_time(inter: discord.Interaction, phase: str):
        await inter.response.send_message(f"Time has been changed to {phase}!", ephemeral=True)


    @staff_group.command(name="weather", description="Set weather")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_weather(inter: discord.Interaction, pattern: str):
        await inter.response.send_message(f"Weather changed to {pattern}!", ephemeral=True)


    @staff_group.command(name="ban", description="Log a permanent ban")
    @staff_guard(["Admin"])
    async def staff_ban(inter: discord.Interaction, member: discord.Member, reason: str):
        log_punishment("BAN", member, reason, inter.user)
        await inter.response.send_message(
            f"{member.display_name} has been **PERMANENTLY** banned for '{reason}'.",
            ephemeral=True
        )


    @staff_group.command(name="mute", description="Temporarily mute a player")
    @staff_guard(["Moderator", "Admin"])
    async def staff_mute(
        inter: discord.Interaction,
        member: discord.Member,
        duration: int,
        reason: Optional[str] = None
    ):
        log_punishment("MUTE", member, reason or "no reason", inter.user)
        await inter.response.send_message(
            f"🔇 {member.display_name} has been muted for {duration} minutes.",
            ephemeral=True
        )


    @staff_group.command(name="kick", description="Kick a player")
    @staff_guard(["Trial Staff", "Mod", "Admin", "Event Planner", "Head Admin", "Beta Tester", "Owner"])
    async def staff_kick(inter: discord.Interaction, member: discord.Member, reason: str):
        await inter.response.send_message(
            f"{member.display_name} has been kicked for {reason}!",
            ephemeral=True
        )


    @staff_group.command(name="warn", description="Warn a player")
    @staff_guard(["Trial Staff", "Mod", "Admin", "Event Planner", "Head Admin", "Beta Tester", "Owner"])
    async def staff_warn(inter: discord.Interaction, member: discord.Member, reason: str):
        await inter.response.send_message(
            f"{member.display_name} has been warned for {reason}!",
            ephemeral=True
        )


    @staff_group.command(name="teleport", description="Teleport a player")
    @staff_guard(["Mod", "Admin", "Event Planner", "Head Admin", "Beta Tester", "Owner"])
    async def staff_teleport(inter: discord.Interaction, member: discord.Member):
        await inter.response.send_message(
            f"{member.display_name} has been teleported!",
            ephemeral=True
        )