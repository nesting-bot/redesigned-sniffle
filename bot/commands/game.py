"""
User‑accessible grow / teleport / weather / time / announce commands
that forward to your ngrok backend.

• Grow command now uses an interactive, button‑driven workflow (see views.py).
• Teleport, Weather, and Time commands add confirmation / selection views,
  cooldown handling, and automatic reversion of weather.
• Announce command forwards any ≤255‑char string to the backend.
"""

from __future__ import annotations

import asyncio, random, time
import discord
from discord import app_commands

from ..nest.views import (
    GrowStartView,
    TeleportConfirmView,
    WeatherSelectView,
    TimeSelectView,
)
from ..utils.io_utils import load_steam_ids, load_balances, save_balances
from ..utils.remote_utils import post_action, backend_available
from ..economy.boosts import is_event_active
from ..utils.discord_helpers import (
    get_cooldown_time_left,
    set_cooldown,
)
from ..utils.logging_utils import log_action
from ..bot_config import (
    GROW_FISH_COST,
    PERSONAL_GROW_CD,
    PERSONAL_TP_CD,
    GLOBAL_WEATHER_CD,
    GLOBAL_TIME_CD,
    WEATHER_REVERT_RANGE,
)

# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
#  In‑memory *global* cooldown registry (guild‑wide)
# --------------------------------------------------------------------------- #
_global_cd: dict[str, float] = {
    "weather": 0.0,
    "time":    0.0,
}
_global_cd_by: dict[str, int] = {
    "weather": 0,
    "time":    0,
}
_global_cd_type: dict[str, str] = {
    "weather": "",
    "time":    "",
}

# --------------------------------------------------------------------------- #
#  Helper functions
# --------------------------------------------------------------------------- #
async def _post(endpoint: str, payload: dict, inter: discord.Interaction, log_msg: str):
    """
    Low‑level wrapper around post_action that also logs & handles backend errors.
    """
    try:
        await post_action(endpoint, payload)
    except Exception as e:                                   # noqa: BLE001
        await inter.response.send_message(
            f"Backend error: {str(e)}",
            ephemeral=True,
        )
        return False
    log_action(inter.user.name, inter.user.id, log_msg)
    return True


def _steam_record_for(discord_id: int) -> dict | None:
    """Return {"steam_id": str, "nickname": str} or None."""
    return load_steam_ids().get(str(discord_id))


def _valid_steam_id(steam_id: str) -> bool:
    return steam_id.isdigit() and len(steam_id) == 17


def _fish_balance(discord_id: int) -> int:
    return load_balances().get(str(discord_id), {"fish": 0}).get("fish", 0)


def _charge_fish(discord_id: int, amount: int) -> None:
    bal = load_balances()
    user_bal = bal.get(str(discord_id), {"fish": 0, "meat": 0})
    user_bal["fish"] = max(0, user_bal["fish"] - amount)
    bal[str(discord_id)] = user_bal
    save_balances(bal)


async def _personal_cd_check(
    inter: discord.Interaction,
    endpoint: str,
    limit_seconds: int,
) -> bool:
    """
    Check / set a **personal** cooldown.  
    Returns True if the user **is allowed** to proceed, otherwise sends the cooldown
    message and returns False.
    """
    if remaining := get_cooldown_time_left(inter.user.id, endpoint, limit_seconds):
        m, s = divmod(remaining, 60)
        await inter.response.send_message(
            f"Please wait {m}m{s}s before another {endpoint}.",
            ephemeral=True,
        )
        return False
    # no cooldown – set it
    set_cooldown(inter.user.id, endpoint)
    return True


def _global_cd_check(endpoint: str, limit_seconds: int) -> float:
    """
    Returns time remaining (seconds) if on cooldown, 0 if free.
    """
    elapsed = time.time() - _global_cd.get(endpoint, 0.0)
    return max(0.0, limit_seconds - elapsed)


# --------------------------------------------------------------------------- #
#  Cog / command registration
# --------------------------------------------------------------------------- #
def setup(client) -> None:     # noqa: PLR0915
    tree = client.tree

    # --------------------------------------------------------------------- #
    # /grow
    # --------------------------------------------------------------------- #
    @tree.command(name="grow", description="Grow your animal – interactive workflow")
    async def grow_cmd(inter: discord.Interaction):  # noqa: ANN001
        if not backend_available():
            return await inter.response.send_message(
                "Sorry, Nesting Bot is not in‑game right now. Please try again later.",
                ephemeral=True,
            )

        if not await _personal_cd_check(inter, "grow", PERSONAL_GROW_CD):
            return

        steam_rec = _steam_record_for(inter.user.id)
        if steam_rec is None:
            return await inter.response.send_message(
                "You haven’t linked a Steam ID yet – use /nest first.",
                ephemeral=True,
            )

        # compute cost info (may be free‑grow event)
        needs_payment = not is_event_active("free_grow")
        fish_have     = _fish_balance(inter.user.id)
        fish_after    = fish_have - GROW_FISH_COST

        view = GrowStartView(
            steam_rec=steam_rec,
            needs_payment=needs_payment,
            fish_have=fish_have,
            fish_after=fish_after,
            inter=inter,
        )
        await inter.response.send_message(
            "Is this grow for you or someone else?",
            view=view,
            ephemeral=True,
        )

    # --------------------------------------------------------------------- #
    # /teleport
    # --------------------------------------------------------------------- #
    @tree.command(name="teleport", description="Teleport yourself to Nesting Bot")
    async def teleport_cmd(inter: discord.Interaction):  # noqa: ANN001
        if not backend_available():
            return await inter.response.send_message(
                "Sorry, Nesting Bot is not in‑game right now. Please try again later.",
                ephemeral=True,
            )

        if not await _personal_cd_check(inter, "teleport", PERSONAL_TP_CD):
            return

        steam_rec = _steam_record_for(inter.user.id)
        if steam_rec is None:
            return await inter.response.send_message(
                "You haven’t linked a Steam ID yet – use /nest first.",
                ephemeral=True,
            )

        view = TeleportConfirmView(steam_rec=steam_rec, inter=inter)
        await inter.response.send_message(
            "Would you like to be teleported to Nesting Bot in‑game?",
            view=view,
            ephemeral=True,
        )

    # --------------------------------------------------------------------- #
    # /weather
    # --------------------------------------------------------------------- #
    @tree.command(name="weather", description="Change the in‑game weather")
    async def weather_cmd(inter: discord.Interaction):  # noqa: ANN001
        if not backend_available():
            return await inter.response.send_message(
                "Sorry, Nesting Bot is not in‑game right now. Please try again later.",
                ephemeral=True,
            )

        remaining = _global_cd_check("weather", GLOBAL_WEATHER_CD)
        if remaining > 0:
            m, s = divmod(int(remaining), 60)
            await inter.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"<@{_global_cd_by['weather']}> last changed the weather "
                        f"to **{_global_cd_type['weather']}** – please wait {m}m{s}s."
                    )
                ),
                ephemeral=True,
            )
            return

        view = WeatherSelectView(inter)
        await inter.response.send_message(
            "What would you like to change the in‑game weather to?",
            view=view,
            ephemeral=True,
        )

    # --------------------------------------------------------------------- #
    # /time
    # --------------------------------------------------------------------- #
    @tree.command(name="time", description="Change the in‑game time (2400‑tick day)")
    async def time_cmd(inter: discord.Interaction):  # noqa: ANN001
        if not backend_available():
            return await inter.response.send_message(
                "Sorry, Nesting Bot is not in‑game right now. Please try again later.",
                ephemeral=True,
            )

        remaining = _global_cd_check("time", GLOBAL_TIME_CD)
        if remaining > 0:
            m, s = divmod(int(remaining), 60)
            await inter.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"<@{_global_cd_by['time']}> last changed the time "
                        f"to **{_global_cd_type['time']}** – please wait {m}m{s}s."
                    )
                ),
                ephemeral=True,
            )
            return

        view = TimeSelectView(inter)
        await inter.response.send_message(
            "What would you like to set the in‑game time to?",
            view=view,
            ephemeral=True,
        )

    # --------------------------------------------------------------------- #
    # /announce
    # --------------------------------------------------------------------- #
    @tree.command(name="announce", description="Send a server‑wide announcement")
    @app_commands.describe(message="Text (≤255 chars) to broadcast in‑game")
    async def announce_cmd(inter: discord.Interaction, message: str):  # noqa: ANN001
        if len(message) > 255:
            return await inter.response.send_message(
                "❌ Announcements are limited to **255** characters.",
                ephemeral=True,
            )
        if not backend_available():
            return await inter.response.send_message(
                "Sorry, Nesting Bot is not in‑game right now. Please try later.",
                ephemeral=True,
            )

        # immediate fire‑and‑forget
        ok = await _post(
            "announce",
            {"message": message},
            inter,
            f"/announce '{message}'",
        )
        if ok:
            await inter.response.send_message("Announcement sent ✅", ephemeral=True)

    # --------------------------------------------------------------------- #
    # /health (unchanged)
    # --------------------------------------------------------------------- #
    @tree.command(name="health", description="Show backend connection status")
    async def health_cmd(inter: discord.Interaction):  # noqa: ANN001
        status = "online ✅" if backend_available() else "offline ❌"
        await inter.response.send_message(f"Backend is **{status}**.", ephemeral=True)

    # --------------------------------------------------------------------- #
    #  Public helpers for views.py – imported to avoid circular refs
    # --------------------------------------------------------------------- #
    async def _finalize_grow(
        inter: discord.Interaction,
        target_steam: str,
        target_nick: str | None,
        needs_payment: bool,
    ):
        """Called by views when the user presses the final **Grow!** button."""
        if needs_payment:
            _charge_fish(inter.user.id, GROW_FISH_COST)

        ok = await _post(
            "grow",
            {"steam_id": target_steam, "nickname": target_nick or ""},
            inter,
            f"/grow {target_steam}",
        )
        if ok:
            await inter.followup.send("✅ Grow request sent!", ephemeral=True)

    async def _execute_teleport(inter: discord.Interaction, steam_rec: dict):
        ok = await _post(
            "teleport",
            {"steam_id": steam_rec["steam_id"], "nickname": steam_rec["nickname"]},
            inter,
            "/teleport",
        )
        if ok:
            await inter.followup.send("✅ Teleport requested – check your game!", ephemeral=True)

    async def _execute_weather(inter: discord.Interaction, pattern_human: str, pattern_machine: str):
        # send to backend
        ok = await _post(
            "weather",
            {"pattern": pattern_machine},
            inter,
            f"/weather {pattern_machine}",
        )
        if not ok:
            return

        # set global cooldown
        _global_cd["weather"]      = time.time()
        _global_cd_by["weather"]   = inter.user.id
        _global_cd_type["weather"] = pattern_human

        await inter.followup.send(
            f"✅ Weather changed to **{pattern_human}**!",
            ephemeral=True,
        )

        # schedule automatic revert to sun
        delay = random.randint(*WEATHER_REVERT_RANGE)
        async def _revert():  # noqa: WPS430
            await asyncio.sleep(delay)
            try:
                await post_action("weather", {"pattern": "sun"})
            except Exception:                                # noqa: BLE001
                pass  # silent – revert isn’t mission‑critical
        asyncio.create_task(_revert())

    async def _execute_time(inter: discord.Interaction, phase_human: str, tick_value: int):
        ok = await _post(
            "time",
            {"ticks": tick_value},
            inter,
            f"/time {tick_value}",
        )
        if not ok:
            return

        _global_cd["time"]      = time.time()
        _global_cd_by["time"]   = inter.user.id
        _global_cd_type["time"] = phase_human

        await inter.followup.send(f"✅ Time set to **{phase_human}**!", ephemeral=True)

    # expose helpers to views
    game_helpers = {
        "finalize_grow":   _finalize_grow,
        "execute_tp":      _execute_teleport,
        "execute_weather": _execute_weather,
        "execute_time":    _execute_time,
    }

