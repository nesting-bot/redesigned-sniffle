"""
Minimal entry‑point so `python -m cenocolors.bot` or `python bot.py` works.
"""

from bot import run_bot   # noqa: E402  (import after venv resolves)

if __name__ == "__main__":
    run_bot()
