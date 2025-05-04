import asyncio, aiohttp, time
from typing import Literal

from ..bot_config import NGROK_URL, NGROK_USER, NGROK_PASS

_backend_ok: bool = False              # module‑level flag

def backend_available() -> bool:
    return _backend_ok

def set_backend_status(val: bool):
    global _backend_ok
    _backend_ok = val


async def post_action(endpoint: Literal["grow", "teleport"], payload: dict) -> str:
    """
    Sends JSON payload to NGROK_URL/<endpoint> using basic‑auth.
    Raises aiohttp.ClientError on failure / non‑2xx / timeout.
    """
    url = f"{NGROK_URL}/{endpoint}"
    auth = aiohttp.BasicAuth(NGROK_USER, NGROK_PASS)
    async with aiohttp.ClientSession(auth=auth) as sess:
        async with sess.post(url, json=payload, timeout=10) as resp:
            resp.raise_for_status()
            return await resp.text()


# ------------------------------------------------------------------ #
# background probe every 60 s – updates backend_available() flag
# ------------------------------------------------------------------ #
async def background_health_probe(client):
    if not NGROK_URL:
        print("NGROK_URL not set – skipping health probe.")
        set_backend_status(False)
        return
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{NGROK_URL}/health", timeout=5) as r:
                    ok = (await r.text()).strip().lower() == "ok"
        except Exception:
            ok = False
        set_backend_status(ok)
        await asyncio.sleep(60)
