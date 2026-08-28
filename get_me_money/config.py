"""Configuration with safe production defaults."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("GMM_DATA_DIR", str(ROOT_DIR / "data"))).expanduser().resolve()
OPPORTUNITIES_DB = DATA_DIR / "opportunities.jsonl"
ATTEMPTS_DB = DATA_DIR / "attempts.jsonl"
STRATEGIES_DB = DATA_DIR / "strategies.jsonl"
DASHBOARD_DB = DATA_DIR / "dashboard.json"
WORK_DIR = DATA_DIR / "work"


@dataclass
class Budget:
    daily_cap: float = 1.00
    per_attempt_cap: float = 0.25
    lifetime_cap: float = 5.00
    min_reward: float = 1.00
    min_ev: float = 0.05
    min_success_probability: float = 0.05


@dataclass
class PlatformConfig:
    # Only verified live paths are enabled in v0.
    taskmarket_enabled: bool = True
    superteam_enabled: bool = True  # discovery; auto-submit is conservative
    gigs_enabled: bool = True
    bounty_enabled: bool = False
    algora_enabled: bool = False
    opire_enabled: bool = False
    clustly_enabled: bool = False

    superteam_key: str = ""
    superteam_telegram: str = ""

    def load_env(self) -> None:
        self.superteam_key = os.getenv("SUPERTEAM_KEY", self.superteam_key)
        self.superteam_telegram = os.getenv("SUPERTEAM_TELEGRAM", self.superteam_telegram)


@dataclass
class HermesConfig:
    binary: str = "hermes"
    provider: str = ""
    model: str = ""
    timeout_seconds: int = 1800
    max_turns: int = 120
    home: str = ""
    passthrough_env: str = ""

    def load_env(self) -> None:
        self.binary = os.getenv("HERMES_BIN", self.binary)
        self.provider = os.getenv("HERMES_PROVIDER", self.provider)
        self.model = os.getenv("HERMES_MODEL", self.model)
        self.timeout_seconds = int(os.getenv("HERMES_TIMEOUT_SECONDS", self.timeout_seconds))
        self.max_turns = int(os.getenv("HERMES_MAX_TURNS", self.max_turns))
        self.home = os.getenv("GMM_HERMES_HOME", self.home)
        self.passthrough_env = os.getenv("GMM_WORKER_PASSTHROUGH_ENV", self.passthrough_env)


@dataclass
class Config:
    budget: Budget = field(default_factory=Budget)
    platforms: PlatformConfig = field(default_factory=PlatformConfig)
    hermes: HermesConfig = field(default_factory=HermesConfig)
    scan_interval_seconds: int = 300
    max_attempts_per_cycle: int = 1
    notify_target: str = ""
    data_dir: Path = DATA_DIR
    work_dir: Path = WORK_DIR
    log_level: str = "INFO"

    def load(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = self.data_dir / "config.json"
        if cfg_path.exists():
            raw = json.loads(cfg_path.read_text())
            for section_name, target in (("budget", self.budget), ("platforms", self.platforms), ("hermes", self.hermes)):
                for k, v in raw.get(section_name, {}).items():
                    if hasattr(target, k) and not k.endswith("_key"):
                        setattr(target, k, v)
            self.scan_interval_seconds = int(raw.get("scan_interval_seconds", self.scan_interval_seconds))
            self.max_attempts_per_cycle = int(raw.get("max_attempts_per_cycle", self.max_attempts_per_cycle))
            self.notify_target = str(raw.get("notify_target", self.notify_target))
            self.log_level = str(raw.get("log_level", self.log_level))

        # Environment always wins over disk config.
        self.platforms.load_env()
        self.hermes.load_env()
        self.notify_target = os.getenv("GMM_NOTIFY_TARGET", self.notify_target)
        self.scan_interval_seconds = int(os.getenv("GMM_SCAN_INTERVAL_SECONDS", self.scan_interval_seconds))
        self.max_attempts_per_cycle = int(os.getenv("GMM_MAX_ATTEMPTS_PER_CYCLE", self.max_attempts_per_cycle))
        self.save_public()

    def save_public(self) -> None:
        cfg_path = self.data_dir / "config.json"
        cfg_path.write_text(json.dumps({
            "budget": self.budget.__dict__,
            "platforms": {k: v for k, v in self.platforms.__dict__.items() if not k.endswith("_key") and k != "superteam_telegram"},
            "hermes": self.hermes.__dict__,
            "scan_interval_seconds": self.scan_interval_seconds,
            "max_attempts_per_cycle": self.max_attempts_per_cycle,
            "notify_target": self.notify_target,
            "log_level": self.log_level,
        }, indent=2))
