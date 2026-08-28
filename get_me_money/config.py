"""Configuration and budget controls."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OPPORTUNITIES_DB = DATA_DIR / "opportunities.jsonl"
ATTEMPTS_DB = DATA_DIR / "attempts.jsonl"
STRATEGIES_DB = DATA_DIR / "strategies.jsonl"
DASHBOARD_DB = DATA_DIR / "dashboard.json"


@dataclass
class Budget:
    daily_cap: float = 5.00          # max daily spend
    per_attempt_cap: float = 2.00    # max single attempt cost
    lifetime_cap: float = 50.00      # hard stop
    min_reward: float = 1.00         # ignore opportunities below this
    min_ev: float = 0.50             # min EV to attempt


@dataclass
class PlatformConfig:
    bounty_enabled: bool = True
    algora_enabled: bool = True
    opire_enabled: bool = True
    clustly_enabled: bool = True
    superteam_enabled: bool = True
    taskmarket_enabled: bool = True
    agenthansa_enabled: bool = False   # 0 active quests currently
    olas_enabled: bool = False       # harder entry, enable later
    virtuals_enabled: bool = False   # skewed economy
    moltjobs_enabled: bool = False   # 0 jobs currently
    sporeagent_enabled: bool = False  # stale

    # API keys / auth (loaded from env)
    bounty_api_key: str = ""
    algora_token: str = ""
    opire_token: str = ""
    clustly_token: str = ""
    superteam_key: str = ""
    taskmarket_api_key: str = ""
    agenthansa_api_key: str = ""

    def load_env(self) -> None:
        self.bounty_api_key = os.getenv("BOUNTY_API_KEY", self.bounty_api_key)
        self.algora_token = os.getenv("ALGORA_TOKEN", self.algora_token)
        self.opire_token = os.getenv("OPIRE_TOKEN", self.opire_token)
        self.clustly_token = os.getenv("CLUSTLY_TOKEN", self.clustly_token)
        self.superteam_key = os.getenv("SUPERTEAM_KEY", self.superteam_key)
        self.taskmarket_api_key = os.getenv("TASKMARKET_API_KEY", self.taskmarket_api_key)
        self.agenthansa_api_key = os.getenv("AGENTHANSA_API_KEY", self.agenthansa_api_key)


@dataclass
class Config:
    budget: Budget = field(default_factory=Budget)
    platforms: PlatformConfig = field(default_factory=PlatformConfig)
    scan_interval_seconds: int = 300
    max_concurrent_attempts: int = 2
    data_dir: Path = DATA_DIR
    log_level: str = "INFO"

    def load(self) -> None:
        self.platforms.load_env()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = self.data_dir / "config.json"
        if cfg_path.exists():
            raw = json.loads(cfg_path.read_text())
            if "budget" in raw:
                for k, v in raw["budget"].items():
                    if hasattr(self.budget, k):
                        setattr(self.budget, k, v)
            if "platforms" in raw:
                for k, v in raw["platforms"].items():
                    if hasattr(self.platforms, k):
                        setattr(self.platforms, k, v)
        self.save()

    def save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = self.data_dir / "config.json"
        cfg_path.write_text(json.dumps({
            "budget": self.budget.__dict__,
            "platforms": {
                k: v for k, v in self.platforms.__dict__.items()
                if not k.endswith("_key") and not k.endswith("_token")
            },
            "scan_interval_seconds": self.scan_interval_seconds,
            "max_concurrent_attempts": self.max_concurrent_attempts,
            "log_level": self.log_level,
        }, indent=2))
