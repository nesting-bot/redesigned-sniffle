"""
decode_obfuscation_code() + tiny colour helpers.
"""

from __future__ import annotations

import json
from typing import Dict

from ..bot_config import OBFUSCATION_JSON_PATH


def decode_obfuscation_code(code_str: str) -> Dict[str, str]:
    if len(code_str) != 16:
        raise ValueError("Code must be exactly 16 characters long.")

    with open(OBFUSCATION_JSON_PATH, "r", encoding="utf-8") as f:
        obf = json.load(f)

    species_map, gender_map, color_map = (
        obf["species"],
        obf["gender"],
        obf["colors"],
    )
    species_rev = {v: k for k, v in species_map.items()}
    gender_rev = {v: k for k, v in gender_map.items()}
    color_rev = {v: k for k, v in color_map.items()}

    sp_code, gd_code = code_str[:3], code_str[3]
    c1_code, c2_code, c3_code, ce_code = (
        code_str[4:7],
        code_str[7:10],
        code_str[10:13],
        code_str[13:16],
    )

    for label, mapping in [
        (sp_code, species_rev),
        (gd_code, gender_rev),
        (c1_code, color_rev),
        (c2_code, color_rev),
        (c3_code, color_rev),
        (ce_code, color_rev),
    ]:
        if label not in mapping:
            raise ValueError(f"Unknown code segment: {label}")

    return {
        "species": species_rev[sp_code],
        "gender": gender_rev[gd_code],
        "c1": color_rev[c1_code].upper(),
        "c2": color_rev[c2_code].upper(),
        "c3": color_rev[c3_code].upper(),
        "ce": color_rev[ce_code].upper(),
    }
