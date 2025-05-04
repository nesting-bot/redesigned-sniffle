"""
All colour‑pack related I/O.
"""

from typing import Dict, List, Tuple

from ..bot_config import COLORPACKS_JSON_PATH
from .io_utils import _json_load

# ----------------------------------------------------------------------- #
# Permissions map
# ----------------------------------------------------------------------- #
def load_colorpack_meta() -> Dict[str, List[str]]:
    raw = _json_load(COLORPACKS_JSON_PATH, {})
    return raw.get("__permissions", {})


# ----------------------------------------------------------------------- #
# Hex‑to‑(pack,label) reverse look‑up
# ----------------------------------------------------------------------- #
def load_colorpacks_reverse() -> Dict[str, Tuple[str, str]]:
    raw = _json_load(COLORPACKS_JSON_PATH, {})
    raw.pop("__permissions", None)
    rev = {}
    for pack, colors in raw.items():
        for label, hexv in colors.items():
            rev[("#" + hexv.lstrip("#")).upper()] = (pack, label)
    return rev
