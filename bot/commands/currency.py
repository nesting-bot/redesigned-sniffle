# bot/commands/currency.py
import random
import discord
from discord.ext import commands
from discord import app_commands
from ..utils.io_utils import load_balances, save_balances, load_messages
from ..utils.logging_utils import log_action
from ..utils.discord_helpers import get_cooldown_time_left, set_cooldown
from ..economy.currency import calc_fish, calc_meat
from ..bot_config import FISHING_COMMAND_COOLDOWN, HUNTING_COMMAND_COOLDOWN

def _cooldown_fail(inter, rem: int, cmd_name: str):
    m, s = divmod(rem, 60)
    msg = random.choice(
        load_messages().get("cooldown",
                            [f"You need to wait {{time_left}} before {cmd_name} again."])
    )
    return inter.response.send_message(
        embed=discord.Embed(description=msg.format(time_left=f"{m}m{s}s"),
                            color=discord.Color.red()),
        ephemeral=True,
    )

def _pay(member_id: int, currency: str, amount: int) -> int:
    bal = load_balances()
    bal.setdefault(str(member_id), {"fish": 0, "meat": 0})
    bal[str(member_id)][currency] += amount
    save_balances(bal)
    return bal[str(member_id)][currency]

class CurrencyCog(commands.Cog, name="currency"):
    """/fish, /hunt, /balance"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /fish --------------------------------------------------------------
    @app_commands.command(name="fish", description="Go 🐟!")
    async def fish_cmd(self, inter: discord.Interaction):
        log_action(inter.user.name, inter.user.id, "/fish")
        if (rem := get_cooldown_time_left(inter.user.id, "fish", FISHING_COMMAND_COOLDOWN)):
            return await _cooldown_fail(inter, rem, "fishing")

        set_cooldown(inter.user.id, "fish")
        earned = calc_fish(inter.user)
        new_bal = _pay(inter.user.id, "fish", earned)

        tpl = random.choice(
            load_messages().get("fish",
                                ["You caught **{earned}** 🐟! Balance: **{balance}** 🐟."])
        )
        await inter.response.send_message(
            embed=discord.Embed(description=tpl.format(earned=earned, balance=new_bal),
                                color=discord.Color.green())
        )

    # /hunt --------------------------------------------------------------
    @app_commands.command(name="hunt", description="Go hunting for 🥩!")
    async def hunt_cmd(self, inter: discord.Interaction):
        log_action(inter.user.name, inter.user.id, "/hunt")
        if (rem := get_cooldown_time_left(inter.user.id, "hunt", HUNTING_COMMAND_COOLDOWN)):
            return await _cooldown_fail(inter, rem, "hunting")

        set_cooldown(inter.user.id, "hunt")
        earned = calc_meat(inter.user)
        new_bal = _pay(inter.user.id, "meat", earned)

        tpl = random.choice(
            load_messages().get("hunt",
                                ["You hunted **{earned}** 🥩! Balance: **{balance}** 🥩."])
        )
        await inter.response.send_message(
            embed=discord.Embed(description=tpl.format(earned=earned, balance=new_bal),
                                color=discord.Color.green())
        )

    # /balance (and /bal alias) -----------------------------------------
    async def _balance_impl(self, inter: discord.Interaction):
        bal = load_balances().get(str(inter.user.id), {"fish": 0, "meat": 0})
        await inter.response.send_message(
            embed=discord.Embed(
                title="Your Balances",
                description=f"🐟 Fish: **{bal['fish']}**\n🥩 Meat: **{bal['meat']}**",
                color=discord.Color.blue(),
            ),
            ephemeral=True,
        )

    @app_commands.command(name="balance", description="Shows your 🐟 / 🥩 balance")
    async def balance_cmd(self, inter: discord.Interaction):
        await self._balance_impl(inter)

    @app_commands.command(name="bal", description="Alias for /balance")
    async def bal_cmd(self, inter: discord.Interaction):
        await self._balance_impl(inter)

# called by bot.load_extension(...)
async def setup(bot: commands.Bot):
    await bot.add_cog(CurrencyCog(bot))
