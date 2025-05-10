"""
All environment variables, path constants, IDs, directory creation, etc.
Never import discord.py here – keep it pure config.
"""
from __future__ import annotations

import os
from pathlib import Path

# ----------------------------------------------------------------------- #
# Environment
# ----------------------------------------------------------------------- #
load_dotenv = __import__("dotenv").load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]        # /cenocolors
load_dotenv(BASE_DIR / ".env")                        # .env in project root

# Tokens / credentials -------------------------------------------------- #
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# SFTP Server (Bisect)
HOSTNAME = os.getenv("SFTP_HOSTNAME", "")
SFTP_PORT = int(os.getenv("SFTP_PORT", "2022"))
USERNAME = os.getenv("SFTP_USERNAME", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")

# NGROK (Nesting Bot)
NGROK_URL  = os.getenv("NGROK_URL", "").rstrip("/")
NGROK_USER = os.getenv("NGROK_USER", "")
NGROK_PASS = os.getenv("NGROK_PASS", "")


# Discord IDs ----------------------------------------------------------- #
TEST_GUILD_ID = 1268612750452592740                   # dev guild
EVENT_CHANNEL_ID = 1361545723598078012                # announcements

# Path constants -------------------------------------------------------- #
DATA_DIR   = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
CACHE_DIR  = BASE_DIR / "sav_cache"
LOG_DIR    = BASE_DIR / "logs"
SAVES_DIR  = BASE_DIR / "saves"

# individual JSON / log files
STEAM_IDS_FILE        = DATA_DIR / "steam_ids.json"
OBFUSCATION_JSON_PATH = DATA_DIR / "obfuscation.json"
BALANCES_FILE         = DATA_DIR / "balance.json"
COOLDOWNS_FILE        = DATA_DIR / "command_cooldowns.json"
MESSAGES_FILE         = DATA_DIR / "messages.json"

COLORPACKS_JSON_PATH  = STATIC_DIR / "colorpacks.json"
SPECIES_LIST_JSON     = STATIC_DIR / "species_list.json"
GENDER_LIST_JSON      = STATIC_DIR / "gender_list.json"

LOG_FILE              = LOG_DIR / "log.txt"
PUNISHMENT_LOG_FILE   = LOG_DIR / "punishment_log.txt"

## Command Cooldowns
FISHING_COMMAND_COOLDOWN = (30 * 60) #     /fish -- 30 Minutes -- /commands/currency.py
HUNTING_COMMAND_COOLDOWN = (60 * 60) #     /hunt -- 60 Minutes -- /commands/currency.py

PERSONAL_GROW_CD         = ( 5 * 60)      #         5  Minutes     -- /commands/game.py
PERSONAL_TP_CD           = (15 * 60)      #         15 Minutes    -- /commands/game.py
GLOBAL_WEATHER_CD        = (30 * 60)      #         30 Minutes    -- /commands/game.py
GLOBAL_TIME_CD           = (10 * 60)      #         10 Minutes    -- /commands/game.py
WEATHER_REVERT_RANGE     = (13*60, 20*60) #         13‑20 Minutes -- /commands/game.py

## Costs
GROW_FISH_COST            = 25       # How many 🐟 it takes to /grow with no event



## Mappings
WEATHER_OPTIONS_MAP: dict[str, str] = { #  /nest/views.py -- Determines what weather options the user can choose
#   User's View : In-Game Weather
    "Sunny": "sun",
    "Foggy": "overcast",
    "Rainy": "rain",
    "Lightning Storm": "storm",
    "Snow": "snow",
}

TIME_OPTIONS_MAP: dict[str, int] = { #  /nest/views.py -- Determines what time options the user can choose
#   User's View : In-Game Time
    "Morning": 800,
    "Noon": 1200,
    "Evening": 1600,
    "Night": 100,
}





# Ensure required dirs exist
for _d in (CACHE_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)
