"""
All discord.ui.* Views + Modal flow – unchanged logic, but isolated.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional, Dict

import discord
from discord.ui import View, Button, Modal, TextInput

from ..utils.logging_utils import log_action
from ..utils.discord_helpers import has_any_role
from ..utils.io_utils import (
    load_steam_ids,
    save_steam_ids,
    load_messages,
    _json_load,
)
from ..utils.colorpack import load_colorpacks_reverse
from ..bot_config import SPECIES_LIST_JSON, GENDER_LIST_JSON, WEATHER_OPTIONS_MAP, TIME_OPTIONS_MAP
from .obfuscation import decode_obfuscation_code
from .sav_utils import ensure_cached_sav, upload_sav


# ----------------------------------------------------------------------- #
# Helper look‑ups
# ----------------------------------------------------------------------- #
def _load_species() -> dict:
    return _json_load(SPECIES_LIST_JSON, {})


def _load_gender() -> dict:
    return _json_load(GENDER_LIST_JSON, {})


# ----------------------------------------------------------------------- #
# Views / Modals (identical behaviour as before)
# ----------------------------------------------------------------------- #
def extract_17digit_id(user_input: str) -> str:
    match_url = re.search(r"(?:steamcommunity\.com/profiles/)(\d{17})", user_input)
    if match_url:
        return match_url.group(1)
    match_digits = re.fullmatch(r"\d{17}", user_input)
    if match_digits:
        return match_digits.group(0)
    raise ValueError("Could not find a 17‑digit Steam ID in your input.")

def _lookup_steam_from_discord(mention: str) -> Optional[str]:
    """Resolve a Discord mention / ID to linked SteamID, or None."""
    m = re.match(r"<@!?(\d+)>", mention) or re.match(r"(\d{17,19})", mention)
    if not m:
        return None
    did = m.group(1)
    rec = load_steam_ids().get(str(did))
    return rec["steam_id"] if rec else None


class SteamIdModal(Modal, title="Paste your 17‑digit Steam ID or Profile URL"):
    nickname_input: TextInput = TextInput(
        label="Desired in‑game nickname",
        style=discord.TextStyle.short,
        max_length=32,
        required=True,
    )
    steam_input: TextInput = TextInput(
        label="17‑digit Steam ID or profile URL",
        style=discord.TextStyle.short,
        max_length=300,
        required=True,
    )

    def __init__(self):
        super().__init__(timeout=300)

    async def on_submit(self, interaction: discord.Interaction):
        nickname = self.nickname_input.value.strip()
        user_input = self.steam_input.value.strip()
        try:
            steam_id = extract_17digit_id(user_input)
        except ValueError:
            return await interaction.response.send_message(
                "Could not find a 17‑digit Steam ID. Please re‑run /nest and try again.",
                ephemeral=True,
            )

        all_ids = load_steam_ids()
        if any(u["steam_id"] == steam_id and str(interaction.user.id) != did
               for did,u in all_ids.items()):
            return await interaction.response.send_message(
                "That Steam ID is already linked to another user.", ephemeral=True
            )

        all_ids[str(interaction.user.id)] = {"steam_id": steam_id, "nickname": nickname}
        save_steam_ids(all_ids)
        log_action(interaction.user.name, interaction.user.id, f"Linked Steam ID: {steam_id}")
        await interaction.response.send_message(
            f"Linked **{nickname}** → `{steam_id}`. Run /nest again!", ephemeral=True
        )

class HelpToFindSteamView(discord.ui.View):
    @discord.ui.button(label="Yes, Steam is open!", style=discord.ButtonStyle.success)
    async def steam_open_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        instructions_view = OpenModalView()
        await interaction.response.send_message(
            content=(
                "1) Go to your Steam Profile. This can be done by clicking on your username at the top-left of Steam. "
                "(Next to 'Store','Library', and 'Community')\n"
                "2) Copy the full URL right underneath where you just clicked (e.g. https://steamcommunity.com/profiles/765611980xxxx).\n"
                "3) Click the button below to paste that link you've copied."
            ),
            view=instructions_view,
            ephemeral=True
        )
        self.stop()

    @discord.ui.button(label="No, Steam is not open", style=discord.ButtonStyle.danger)
    async def steam_not_open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "No worries! Please open Steam, navigate to your profile, and come back.",
            ephemeral=True
        )
        self.stop()

class OpenModalView(discord.ui.View):
    @discord.ui.button(label="Enter Steam ID Now", style=discord.ButtonStyle.primary)
    async def open_modal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SteamIdModal())
        self.stop()

class KnowSteamView(discord.ui.View):
    @discord.ui.button(label="I know my Steam ID", style=discord.ButtonStyle.success)
    async def know_id_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SteamIdModal())
        self.stop()

    @discord.ui.button(label="Help, please!", style=discord.ButtonStyle.primary)
    async def need_help_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Let's walk you through finding your Steam ID.\nIs Steam open on your desktop?",
            view=HelpToFindSteamView(),
            ephemeral=True
        )
        self.stop()

class LinkSteamView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Great, let's get started!\n\nDo you know your 17-digit Steam ID?",
            view=KnowSteamView(),
            ephemeral=True
        )
        self.stop()
    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "No problem! Come back anytime with /nest when you’re ready to link.",
            ephemeral=True
        )
        self.stop()








# --------------------------- SlotChoiceView ---------------------------- #
class SlotChoiceView(View):
    def __init__(self, parent_view, obfuscated_code):
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.obfuscated_code = obfuscated_code
        self.selection_made = False

        # dynamically add Slot 1–5 buttons
        for i in range(1, 6):
            btn = Button(label=str(i), style=discord.ButtonStyle.primary)

            # bind a callback that captures i at definition time
            async def slot_callback(interaction: discord.Interaction, idx=i):
                await self._finalise(interaction, str(idx))

            btn.callback = slot_callback
            self.add_item(btn)

        # keep your Exit button as‑is (or add it here if you prefer)
        exit_btn = Button(label="Exit", style=discord.ButtonStyle.danger)
        async def exit_callback(interaction: discord.Interaction):
            await interaction.response.send_message("Cancelled.", ephemeral=True)
            self.stop()
        exit_btn.callback = exit_callback
        self.add_item(exit_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.parent_view.author_id:
            await interaction.response.send_message("This isn't your command.", ephemeral=True)
            return False
        if self.selection_made:
            await interaction.response.send_message("You already selected a slot.", ephemeral=True)
            return False
        return True

    async def _finalise(self, interaction: discord.Interaction, slot: str):
        # … your existing finalisation logic here …
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        self.selection_made = True
        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except discord.NotFound:
            pass
        await interaction.followup.send("Uploading, please wait …", ephemeral=True)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            upload_sav,
            self.parent_view.steam_id,
            slot,
            self.parent_view.cached_path,
            interaction.user.name,
            interaction.user.id,
        )
        await interaction.followup.send(
            f"Success, <@{interaction.user.id}> has been nested!",
            ephemeral=False,
        )
        self.stop()


# ---------------------------- CodeInputModal --------------------------- #
class CodeInputModal(Modal, title="Paste Your Code"):
    code_input: TextInput = TextInput(
        label="Website Code",
        placeholder="A1B2C3D4E5F6G7H8",
        style=discord.TextStyle.short,
        required=True,
        max_length=50,
    )

    def __init__(self, parent_view):
        super().__init__(timeout=300)
        self.parent_view = parent_view
        self.colorpacks_map = load_colorpacks_reverse()

    async def on_submit(self, interaction: discord.Interaction):
        obf_code = self.code_input.value.strip()
        try:
            decoded = decode_obfuscation_code(obf_code)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

        species, gender = decoded["species"], decoded["gender"]
        c1_hex, c2_hex, c3_hex, ce_hex = (
            decoded["c1"],
            decoded["c2"],
            decoded["c3"],
            decoded["ce"],
        )

        # permissions
        used_packs = {self.colorpacks_map["#" + h.upper()][0] for h in (c1_hex, c2_hex, c3_hex, ce_hex)}
        for p in used_packs:
            allowed = self.parent_view.client.pack_permissions.get(p, [])
            if allowed and not has_any_role(interaction.user, allowed):
                return await interaction.response.send_message(
                    f"Colour‑pack **{p}** is restricted. Required roles: {', '.join(allowed)}",
                    ephemeral=True,
                )

        # create cached .sav
        cached_path = ensure_cached_sav(obf_code, species, gender, c1_hex, c2_hex, c3_hex, ce_hex)
        self.parent_view.cached_path = cached_path

        # fancy summary
        species_data, gender_data = _load_species(), _load_gender()
        def lookup_color(hexv: str) -> str:
            key = "#" + hexv.upper()
            return f"{self.colorpacks_map[key][1]} ({self.colorpacks_map[key][0]})" if key in self.colorpacks_map else key

        summary = (
            f"🌿 **Nest Confirmation** 🌿\n"
            f"**Code**: {obf_code}\n\n"
            f"**Species**: {species_data.get(species, species)}\n"
            f"**Gender**:  {gender_data.get(gender, gender)}\n"
            f"**Region 1**: {lookup_color(c1_hex)}\n"
            f"**Region 2**: {lookup_color(c2_hex)}\n"
            f"**Region 3**: {lookup_color(c3_hex)}\n"
            f"**Eyes**:     {lookup_color(ce_hex)}\n\n"
            "Select a slot (1‑5). It will overwrite any existing animal."
        )
        await interaction.response.send_message(
            summary,
            view=SlotChoiceView(self.parent_view, obf_code),
            ephemeral=True,
        )


# ------------------------- Parent view entry point --------------------- #
class NestWorkflowParentView(View):
    def __init__(self, steam_id: str, author_id: int, client):
        super().__init__(timeout=180)
        self.steam_id = steam_id
        self.cached_path = None
        self.author_id = author_id
        self.client = client

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This isn't your command.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def confirmed(self, interaction: discord.Interaction, _btn: Button):
        await interaction.response.send_modal(CodeInputModal(self))
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def declined(self, interaction: discord.Interaction, _btn: Button):
        await interaction.response.send_message(
            "‌‌ \n"
            "Please visit the Animal Builder website to generate a code!\n"
            "https://CenoColors.com",
#            "[CenoColors.com](https://CenoColors.com)",     # This is a "Cleaner" look, but an external link
        )
        self.stop()




# ---------------------------------------------------------------------------
# ▼▼▼  NEW COMMAND WORKFLOWS  ▼▼▼
# ---------------------------------------------------------------------------

# ----------------------------- /grow workflow -----------------------------

def _grow_cost_blurb(needs_payment: bool, have: int, after: int) -> str:
    cost = have - after
    if not needs_payment:
        return "A free‑grow event is active – no 🐟 cost!"
    return (
        f"Growing costs **{cost} 🐟** – you have **{have}**.\n"
        f"After the grow, you will have **{after}🐟** left."
    )


class GrowStartView(View):
    def __init__(
        self,
        *,
        steam_rec: dict,
        needs_payment: bool,
        fish_have: int,
        fish_after: int,
        inter: discord.Interaction,
    ):
        super().__init__(timeout=120)
        self.steam_rec = steam_rec
        self.needs_payment = needs_payment
        self.fish_have = fish_have
        self.fish_after = fish_after
        self.inter = inter

    @discord.ui.button(label="Me", style=discord.ButtonStyle.primary)
    async def me(self, interaction: discord.Interaction, _: Button):  # noqa: ANN001
        await interaction.response.edit_message(
            content=_grow_cost_blurb(self.needs_payment, self.fish_have, self.fish_after),
            view=GrowConfirmSelfView(
                inter=self.inter,
                steam_rec=self.steam_rec,
                needs_payment=self.needs_payment,
            ),
        )

    @discord.ui.button(label="Someone Else", style=discord.ButtonStyle.secondary)
    async def someone(self, interaction: discord.Interaction, _: Button):  # noqa: ANN001
        await interaction.response.edit_message(
            content=_grow_cost_blurb(self.needs_payment, self.fish_have, self.fish_after)
            + "\nDo you want to use their Steam ID or Discord ID?",
            view=GrowTargetMethodView(inter=self.inter, needs_payment=self.needs_payment),
        )


class GrowConfirmSelfView(View):
    def __init__(self, *, inter: discord.Interaction, steam_rec: dict, needs_payment: bool):
        super().__init__(timeout=60)
        self.inter = inter
        self.steam_rec = steam_rec
        self.needs_payment = needs_payment

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, _: Button):  # noqa: ANN001
        helpers = self.inter.client.get_cog("game").game_helpers  # type: ignore[attr-defined]
        await helpers["finalize_grow"](
            self.inter,
            self.steam_rec["steam_id"],
            self.steam_rec["nickname"],
            self.needs_payment,
        )
        await interaction.message.delete(delay=0)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, _: Button):  # noqa: ANN001
        await interaction.response.edit_message(content="Grow cancelled.", view=None)


class GrowTargetMethodView(View):
    def __init__(self, *, inter: discord.Interaction, needs_payment: bool):
        super().__init__(timeout=90)
        self.inter = inter
        self.needs_payment = needs_payment

    @discord.ui.button(label="Accept – Steam ID", style=discord.ButtonStyle.primary)
    async def by_steam(self, interaction: discord.Interaction, _: Button):  # noqa: ANN001
        await interaction.response.send_modal(GrowSteamIDModal(self.inter, self.needs_payment))

    @discord.ui.button(label="Accept – Discord ID", style=discord.ButtonStyle.primary)
    async def by_discord(self, interaction: discord.Interaction, _: Button):  # noqa: ANN001
        await interaction.response.send_modal(GrowDiscordIDModal(self.inter, self.needs_payment))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, _: Button):  # noqa: ANN001
        await interaction.response.edit_message(content="Grow cancelled.", view=None)


class GrowSteamIDModal(Modal, title="Enter a 17‑digit Steam ID"):
    steam_id: TextInput = TextInput(
        label="Steam ID",
        min_length=17,
        max_length=17,
    )

    def __init__(self, inter: discord.Interaction, needs_payment: bool):
        super().__init__()
        self.inter = inter
        self.needs_payment = needs_payment

    async def on_submit(self, interaction: discord.Interaction):  # noqa: ANN001
        sid = str(self.steam_id.value).strip()
        if not sid.isdigit():
            return await interaction.response.send_message("❌ Steam ID must be numeric.", ephemeral=True)
        view = GrowFinalConfirmView(
            inter=self.inter,
            target_steam=sid,
            target_nick=None,
            needs_payment=self.needs_payment,
        )
        await interaction.response.send_message(f"Grow **{sid}**?", view=view, ephemeral=True)


class GrowDiscordIDModal(Modal, title="Enter a Discord mention or ID"):
    discord_id: TextInput = TextInput(label="Discord user")

    def __init__(self, inter: discord.Interaction, needs_payment: bool):
        super().__init__()
        self.inter = inter
        self.needs_payment = needs_payment

    async def on_submit(self, interaction: discord.Interaction):  # noqa: ANN001
        mention = str(self.discord_id.value).strip()
        sid = _lookup_steam_from_discord(mention)
        if sid is None:
            return await interaction.response.send_message(
                "❌ No linked Steam ID found for that Discord user. Please try again with a Steam ID instead.",
                ephemeral=True,
            )
        view = GrowFinalConfirmView(
            inter=self.inter,
            target_steam=sid,
            target_nick=None,
            needs_payment=self.needs_payment,
        )
        await interaction.response.send_message(f"Grow **{mention}** ({sid})?", view=view, ephemeral=True)


class GrowFinalConfirmView(View):
    def __init__(
        self,
        *,
        inter: discord.Interaction,
        target_steam: str,
        target_nick: Optional[str],
        needs_payment: bool,
    ):
        super().__init__(timeout=60)
        self.inter = inter
        self.target_steam = target_steam
        self.target_nick = target_nick
        self.needs_payment = needs_payment

    @discord.ui.button(label="Grow!", style=discord.ButtonStyle.success)
    async def do_grow(self, interaction: discord.Interaction, _: Button):  # noqa: ANN001
        helpers = self.inter.client.get_cog("game").game_helpers  # type: ignore[attr-defined]
        await helpers["finalize_grow"](
            self.inter,
            self.target_steam,
            self.target_nick,
            self.needs_payment,
        )
        await interaction.message.delete(delay=0)

    @discord.ui.button(label="No, Don’t Grow", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, _: Button):  # noqa: ANN001
        await interaction.response.edit_message(content="Grow cancelled.", view=None)


# --------------------------- /teleport confirm ---------------------------- #
class TeleportConfirmView(discord.ui.View):
    def __init__(self, *, steam_rec: dict, inter: discord.Interaction):
        super().__init__(timeout=30)
        self.steam_rec = steam_rec
        self.inter = inter

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes(self, interaction: discord.Interaction, _: discord.ui.Button):  # noqa: ANN001
        helpers = self.inter.client.get_cog("game").game_helpers  # type: ignore[attr-defined]
        await helpers["execute_tp"](self.inter, self.steam_rec)
        await interaction.message.delete(delay=0)

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, _: discord.ui.Button):  # noqa: ANN001
        await interaction.response.edit_message(content="Teleport cancelled.", view=None)


# --------------------------- /weather picker ------------------------------ #
class WeatherSelectView(discord.ui.View):
    def __init__(self, inter: discord.Interaction):
        super().__init__(timeout=90)
        self.inter = inter
        for human, machine in WEATHER_OPTIONS_MAP.items():
            self.add_item(WeatherButton(label=human, machine_code=machine))


class WeatherButton(discord.ui.Button):  # type: ignore[misc]
    def __init__(self, *, label: str, machine_code: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.machine_code = machine_code

    async def callback(self, interaction: discord.Interaction):  # noqa: ANN001
        helpers = interaction.client.get_cog("game").game_helpers  # type: ignore[attr-defined]
        await helpers["execute_weather"](interaction, self.label, self.machine_code)
        await interaction.message.delete(delay=0)


# --------------------------- /time picker --------------------------------- #
class TimeSelectView(discord.ui.View):
    def __init__(self, inter: discord.Interaction):
        super().__init__(timeout=90)
        self.inter = inter
        for human, ticks in TIME_OPTIONS_MAP.items():
            self.add_item(TimeButton(label=human, ticks=ticks))


class TimeButton(discord.ui.Button):  # type: ignore[misc]
    def __init__(self, *, label: str, ticks: int):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.ticks = ticks

    async def callback(self, interaction: discord.Interaction):  # noqa: ANN001
        helpers = interaction.client.get_cog("game").game_helpers  # type: ignore[attr-defined]
        await helpers["execute_time"](interaction, self.label, self.ticks)
        await interaction.message.delete(delay=0)