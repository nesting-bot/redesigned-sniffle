"""
Each sub‑module exposes `setup(client)` which receives the shared CenoClient
instance and registers its slash commands on `client.tree`.
"""

from importlib import import_module
from typing import List

_command_modules: List[str] = ["currency", "staff", "nest", "game"] # When adding additional commands, also go to bot/__init__.py


# on import we *dynamically* load them so `setup()` functions can be discovered
for _mod in _command_modules:
    import_module(f".{_mod}", package=__name__)
