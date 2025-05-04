"""
All sub‑commands under /staff
"""

import time

import discord
from discord import app_commands

from ..economy.boosts import active_boosts, set_event
from ..utils.discord_helpers import has_any_role
from ..utils.io_utils import (
    load_balances,
    load_steam_ids,
)
from ..utils.logging_utils import log_punishment
from ..bot_config import EVENT_CHANNEL_ID, PUNISHMENT_LOG_FILE


# ----------------------------------------------------------------------- #
# Decorator helpers
# ----------------------------------------------------------------------- #
def staff_guard(names):
    def decorator(func):
        async def predicate(inter: discord.Interaction):
            if has_any_role(inter.user, names):
                return True
            await inter.response.send_message("You lack permission.", ephemeral=True)
            return False

        return app_commands.check(predicate)(func)

    return decorator


# ----------------------------------------------------------------------- #
# Registration API
# ----------------------------------------------------------------------- #
def setup(client) -> None:
    tree = client.tree
    staff_group = app_commands.Group(name="staff", description="Staff tools")
    tree.add_command(staff_group, guild=discord.Object(id=client.guilds[0].id))  # local guild copy

    # --------------------------- /staff boost -------------------------- #
    # @staff_group.command(name="boost", description="Start a Fish/Meat boost")
    # @staff_guard(["Beta Tester", "Owner"])
    # @app_commands.describe(
    #     currency="fish or meat",
    #     boost_type="flat or multiplier",
    #     amount="number",
    #     duration="minutes",
    # )
    # async def boost(
    #     inter: discord.Interaction,
    #     currency: str,
    #     boost_type: str,
    #     amount: int,
    #     duration: int,
    # ):
    #     currency, boost_type = currency.lower(), boost_type.lower()
    #     if currency not in ("fish", "meat") or boost_type not in ("flat", "multiplier"):
    #         return await inter.response.send_message("Bad arguments.", ephemeral=True)
    #     active_boosts[currency] = {
    #         "flat": amount if boost_type == "flat" else 0,
    #         "mult": 1 + (amount / 100) if boost_type == "multiplier" else 1,
    #         "expires": time.time() + duration * 60,
    #     }
    #     ends = int(active_boosts[currency]["expires"])
    #     msg = (
    #         f"A **{currency.capitalize()}** event is here! "
    #         f"Gain +{amount}{'%' if boost_type == 'multiplier' else ''} {currency} "
    #         f"for {duration}m. Ends <t:{ends}:R>."
    #     )
    #     await inter.client.get_channel(EVENT_CHANNEL_ID).send(msg)
    #     await inter.response.send_message("Boost applied.", ephemeral=True)


    # TODO: Edit this to incorporate the above features. This is more minimal
    # Replacement code?
    @staff_group.command(name="event", description="Start / stop server events")
    @staff_guard(["Beta Tester", "Owner"])
    @app_commands.describe(event_name="fish_bonus | meat_bonus | free_grow | free_nest",
                        amount="flat or % (currency only)", duration="minutes")
    async def event_cmd(inter: discord.Interaction,
                        event_name: str, amount: int | None, duration: int):
        event_name = event_name.lower()

        if event_name in ("fish_bonus", "meat_bonus"):
            # old behaviour for currency boosts
            currency = "fish" if event_name == "fish_bonus" else "meat"
            active_boosts[currency] = {
                "flat": amount,
                "mult": 1,
                "expires": time.time() + duration * 60
            }
        elif event_name in ("free_grow", "free_nest"):
            set_event(event_name, duration)
        else:
            return await inter.response.send_message("Unknown event.", ephemeral=True)

        await inter.response.send_message(f"Event **{event_name}** started for {duration} m.", ephemeral=True)

    # ------------------------ /staff balance (player) --------------------------- #
    @staff_group.command(name="balance", description="Check a player's balance")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_balance(inter: discord.Interaction, member: discord.Member):
        bal = load_balances().get(str(member.id), {"fish": 0, "meat": 0})
        await inter.response.send_message(
            f"{member.display_name} has {bal['fish']} 🐟 and {bal['meat']} 🥩",
            ephemeral=True,
        )

    # ------------------------ /staff balance (add/remove/set) (fish/meat) --------------------------- #







    # ------------------------- /staff steamid (player) -------------------------- #
    @staff_group.command(name="steamid", description="Show user's Steam ID")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_steamid(inter: discord.Interaction, member: discord.Member):
        sid = load_steam_ids().get(str(member.id))
        await inter.response.send_message(
            f"{member.display_name}'s Steam ID: `{sid or 'None linked'}`", ephemeral=True
        )

    # ------------------------------------------------------------------ #
    # remaining staff sub‑commands: warn/ban/kick/grow/etc.
    # (identical to your original code – copy/paste or extend here)
    # ------------------------------------------------------------------ #
    @staff_group.command(name="logs", description="Get punishment log")
    @staff_guard(["Beta Tester", "Owner", "Admin", "Head Admin"])
    async def staff_logs(inter: discord.Interaction, log_type: str):
        if log_type.lower() != "admin":
            return await inter.response.send_message("Kill logs WIP.", ephemeral=True)
        await inter.response.send_message(
            "Admin log:",
            file=discord.File(PUNISHMENT_LOG_FILE, filename="punishment_log.txt"),
            ephemeral=True)

    @staff_group.command(name="grow", description="Grow a player")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_grow(inter: discord.Interaction,
                        member: discord.Member,
                        stage: app_commands.Choice[str]):
        await inter.response.send_message(
            f"{member.display_name} has been grown to a {stage.value} adult!")

    @staff_group.command(name="time", description="Set in‑game time")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_time(inter: discord.Interaction, phase: str):
        await inter.response.send_message(f"Time has been changed to {phase}!")

    @staff_group.command(name="weather", description="Set weather")
    @staff_guard(["Beta Tester", "Owner"])
    async def staff_weather(inter: discord.Interaction, pattern: str):
        await inter.response.send_message(f"Weather changed to {pattern}!")

    def log_punishment(action: str, member: discord.Member, reason: str, staff: discord.Member):
        ts = int(time.time())
        with open(PUNISHMENT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {staff} -> {member} : {action} : {reason}\n")

    @staff_group.command(name="ban", description="Log a permanent ban")
    @staff_guard(["Owner", "Beta Tester", "Head Admin", "Admin", "Event Planner"])
    async def staff_ban(inter: discord.Interaction, member: discord.Member, reason: str):
        log_punishment("BAN", member, reason, inter.user)
        await inter.response.send_message(
            f"{member.display_name} has been **PERMANENTLY** banned for '{reason}'.")

    @staff_group.command(name="kick", description="Kick a player")
    @staff_guard(["Trial Staff", "Mod", "Admin", "Event Planner", "Head Admin", "Beta Tester", "Owner"])
    async def staff_kick(inter: discord.Interaction, member: discord.Member, reason: str):
        await inter.response.send_message(
            f"{member.display_name} has been kicked for {reason}!")

    @staff_group.command(name="warn", description="Warn a player")
    @staff_guard(["Trial Staff", "Mod", "Admin", "Event Planner", "Head Admin", "Beta Tester", "Owner"])
    async def staff_warn(inter: discord.Interaction, member: discord.Member, reason: str):
        await inter.response.send_message(
            f"{member.display_name} has been warned for {reason}!")

    @staff_group.command(name="teleport", description="Teleport a player")
    @staff_guard(["Mod", "Admin", "Event Planner", "Head Admin", "Beta Tester", "Owner"])
    async def staff_teleport(inter: discord.Interaction, member: discord.Member):
        await inter.response.send_message(f"{member.display_name} has been teleported!")