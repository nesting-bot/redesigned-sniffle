import random
from typing import Callable

import discord
from discord import app_commands

from ..utils.io_utils import (
    load_balances,
    save_balances,
    load_messages,
)
from ..utils.logging_utils import log_action
from ..utils.discord_helpers import get_cooldown_time_left, set_cooldown
from ..economy.currency import calc_fish, calc_meat

from ..bot_config import FISHING_COMMAND_COOLDOWN, HUNTING_COMMAND_COOLDOWN


def _cooldown_fail(inter, rem: int, cmd_name: str) -> None:
    m, s = divmod(rem, 60)
    msg = random.choice(
        load_messages().get("cooldown", [f"You need to wait {{time_left}} before {cmd_name} again."])
    )
    embed = discord.Embed(description=msg.format(time_left=f"{m}m{s}s"), color=discord.Color.red())
    return inter.response.send_message(embed=embed, ephemeral=True)


def _pay(member_id: int, currency: str, amount: int) -> int:
    bal = load_balances()
    bal.setdefault(str(member_id), {"fish": 0, "meat": 0})
    bal[str(member_id)][currency] += amount
    save_balances(bal)
    return bal[str(member_id)][currency]


# ----------------------------------------------------------------------- #
# Registration API
# ----------------------------------------------------------------------- #
def setup(client) -> None:  # receives CenoClient instance
    tree = client.tree

    # ----------------------------- /fish -------------------------------- #
    @tree.command(name="fish", description="Go 🐟!")
    async def fish_cmd(inter: discord.Interaction) -> None:
        log_action(inter.user.name, inter.user.id, "/fish")

        if (rem := get_cooldown_time_left(inter.user.id, "fish", FISHING_COMMAND_COOLDOWN)):
            return await _cooldown_fail(inter, rem, "fishing")

        set_cooldown(inter.user.id, "fish")

        earned = calc_fish(inter.user)
        new_bal = _pay(inter.user.id, "fish", earned)

        tpl = random.choice(
            load_messages().get("fish", ["You caught **{earned}** 🐟! Balance: **{balance}** 🐟."])
        )
        embed = discord.Embed(
            description=tpl.format(earned=earned, balance=new_bal),
            color=discord.Color.green(),
        )
        await inter.response.send_message(embed=embed)

    # ----------------------------- /hunt -------------------------------- #
    @tree.command(name="hunt", description="Go hunting for 🥩!")
    async def hunt_cmd(inter: discord.Interaction) -> None:
        log_action(inter.user.name, inter.user.id, "/hunt")

        if (rem := get_cooldown_time_left(inter.user.id, "hunt", HUNTING_COMMAND_COOLDOWN)):
            return await _cooldown_fail(inter, rem, "hunting")

        set_cooldown(inter.user.id, "hunt")

        earned = calc_meat(inter.user)
        new_bal = _pay(inter.user.id, "meat", earned)

        tpl = random.choice(
            load_messages().get("hunt", ["You hunted **{earned}** 🥩! Balance: **{balance}** 🥩."])
        )
        embed = discord.Embed(
            description=tpl.format(earned=earned, balance=new_bal),
            color=discord.Color.green(),
        )
        await inter.response.send_message(embed=embed)

    # --------------------------- /balance ------------------------------ #
    @tree.command(name="balance", description="Shows your 🐟 / 🥩 balance")
    async def balance_cmd(inter: discord.Interaction) -> None:
        bal = load_balances().get(str(inter.user.id), {"fish": 0, "meat": 0})
        embed = discord.Embed(
            title="Your Balances",
            description=f"🐟 Fish: **{bal['fish']}**\n🥩 Meat: **{bal['meat']}**",
            color=discord.Color.blue(),
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="bal", description="Shows your 🐟 / 🥩 balance")
    async def balance_cmd(inter: discord.Interaction) -> None:
        bal = load_balances().get(str(inter.user.id), {"fish": 0, "meat": 0})
        embed = discord.Embed(
            title="Your Balances",
            description=f"🐟 Fish: **{bal['fish']}**\n🥩 Meat: **{bal['meat']}**",
            color=discord.Color.blue(),
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="justtesting", description="TestCommand")
    async def test_command_here(inter:discord.Interaction) -> None:
        await inter.response.send_message(content="TESTING COMMAND NOW")