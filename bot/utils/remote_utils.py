import asyncio, aiohttp, time
from aiohttp import BasicAuth
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

    print(f"Pointing to url: '{NGROK_URL}'")
    await client.wait_until_ready()

    auth = BasicAuth(NGROK_USER, NGROK_PASS)

    while not client.is_closed():
        try:
            async with aiohttp.ClientSession(auth=auth) as s:
                async with s.get(f"{NGROK_URL}/health", timeout=5) as r:
                    data = await r.json()
                    ok = data.get("status", "").lower() == "ok"
                    print(f"[Health Probe] Backend status: {ok}")
        except Exception as e:
            print(f"[Health Probe] Exception during probe: {e}")
            ok = False
        set_backend_status(ok)
        await asyncio.sleep(60)


async def single_health_check():
    if not NGROK_URL:
        print("NGROK_URL not set – skipping health probe.")
        set_backend_status(False)
        return

    print(f"Checking health at: '{NGROK_URL}/health'")
    auth = BasicAuth(NGROK_USER, NGROK_PASS)

    try:
        async with aiohttp.ClientSession(auth=auth) as s:
            async with s.get(f"{NGROK_URL}/health", timeout=5) as r:
                data = await r.json()
                ok = data.get("status", "").lower() == "ok"
                print(f"[Health Probe Once] Backend status: {ok}")
    except Exception as e:
        print(f"[Health Probe Once] Exception during probe: {e}")
        ok = False

    set_backend_status(ok)
