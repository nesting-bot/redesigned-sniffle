"""
.sav manipulation + SFTP upload
"""

from __future__ import annotations

import os
from pathlib import Path

import paramiko

from ..bot_config import (
    CACHE_DIR,
    SAVES_DIR,
    HOSTNAME,
    SFTP_PORT,
    USERNAME,
    PASSWORD,
)
from ..utils.logging_utils import log_action


def _convert_rgb_to_file_order(hex_color: str) -> bytes:
    hex_color = hex_color.strip().replace("#", "")
    if len(hex_color) != 6:
        raise ValueError(f"Invalid colour '{hex_color}' for .sav replacement.")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return bytes([b, g, r, 0xFF])


def _replace_last_four_whites(
    file_data: bytes, skin1: bytes, skin2: bytes, skin3: bytes, eyes: bytes
) -> bytes:
    white = b"\xFF\xFF\xFF\xFF"
    data = bytearray(file_data)
    indices = [i for i in range(len(data) - 3) if data[i : i + 4] == white]
    if len(indices) < 4:
        raise ValueError("Not enough pure‑white blocks found (need 4).")
    for pos, repl in zip(indices[-4:], (skin1, skin2, skin3, eyes)):
        data[pos : pos + 4] = repl
    return data


# ----------------------------------------------------------------------- #
# Public helpers
# ----------------------------------------------------------------------- #
def ensure_cached_sav(
    obfuscated_code: str,
    species: str,
    gender: str,
    c1_hex: str,
    c2_hex: str,
    c3_hex: str,
    ce_hex: str,
) -> Path:
    cached_path = Path(CACHE_DIR) / f"{obfuscated_code}.sav"
    if cached_path.exists():
        return cached_path

    template = Path(SAVES_DIR) / f"{species}_{gender}.sav"
    if not template.exists():
        raise ValueError(f"Template .sav not found: {template.name}")

    with open(template, "rb") as f:
        original = f.read()

    skins = [_convert_rgb_to_file_order(h) for h in (c1_hex, c2_hex, c3_hex, ce_hex)]
    modified = _replace_last_four_whites(original, *skins)

    with open(cached_path, "wb") as f:
        f.write(modified)
    return cached_path


def _mkdir_p(sftp, remote_directory: str):
    dirs = remote_directory.split("/")
    path = ""
    for directory in dirs:
        if directory:
            path = os.path.join(path, directory)
            try:
                sftp.stat(path)
            except IOError:
                sftp.mkdir(path)


def upload_sav(
    steam_id: str,
    slot: str,
    local_path: Path,
    discord_username: str,
    discord_user_id: int,
):
    remote_path = f"./TheCenozoicEra/Saved/SaveGames/{steam_id} {slot}.sav"

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_client.connect(
            HOSTNAME,
            port=SFTP_PORT,
            username=USERNAME,
            password=PASSWORD,
            look_for_keys=False,
            allow_agent=False,
        )
        sftp = ssh_client.open_sftp()
        _mkdir_p(sftp, os.path.dirname(remote_path))
        sftp.put(str(local_path), remote_path)
        sftp.close()
        log_action(discord_username, discord_user_id, f"SFTP Upload -> {steam_id} slot:{slot}")
    finally:
        ssh_client.close()
