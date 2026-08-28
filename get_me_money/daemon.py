"""Long-running VPS loop with single-process lock."""
from __future__ import annotations
import argparse
import asyncio
import fcntl
import logging
import signal
from pathlib import Path
from get_me_money.config import Config
from get_me_money.main import earn_cycle


async def run(execute: bool) -> None:
    cfg = Config(); cfg.load()
    lock_path = cfg.data_dir / "daemon.lock"; lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = open(lock_path, "w")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("another get-me-money daemon is already running")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    while not stop.is_set():
        try:
            result = await earn_cycle(cfg, execute=execute)
            logging.info("cycle: %s", result.get("status"))
        except Exception:
            logging.exception("earn cycle failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=cfg.scan_interval_seconds)
        except asyncio.TimeoutError:
            pass


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--execute", action="store_true", help="actually submit work; without this daemon is observation-only"); a=p.parse_args()
    cfg=Config(); cfg.load(); logging.basicConfig(level=getattr(logging,cfg.log_level.upper(),logging.INFO), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(run(a.execute))

if __name__ == "__main__": main()
