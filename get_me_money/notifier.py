"""Optional operator notifications via Hermes' configured messaging credentials."""
from __future__ import annotations
import asyncio
import shutil
from get_me_money.config import Config


async def notify(config: Config, message: str) -> None:
    if not config.notify_target:
        return
    binary = shutil.which(config.hermes.binary) or config.hermes.binary
    try:
        p = await asyncio.create_subprocess_exec(
            binary, "send", "--to", config.notify_target, message,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(p.wait(), timeout=20)
    except Exception:
        return
