"""Identity module — agent-native auth patterns.

Supports:
- Composio OAuth (one-time human auth, persistent agent credentials)
- Browserbase persistent sessions (manual MFA once, context persists)
- Native agent API registration (Taskmarket, Superteam, Clustly)
- Human checkpoint detection (CAPTCHA, KYC, age verification)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CREDENTIALS_DIR = Path(__file__).parent.parent.parent / "data" / "credentials"


@dataclass
class AuthSession:
    platform: str
    auth_type: str  # "api_key", "oauth", "browser_session", "wallet"
    credentials: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    refreshed_at: float = 0.0
    human_required: bool = False
    human_checkpoint_reason: str = ""

    @property
    def is_valid(self) -> bool:
        if self.human_required:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return bool(self.credentials)

    @property
    def needs_refresh(self) -> bool:
        if not self.expires_at:
            return False
        return time.time() > self.expires_at - 3600  # refresh 1hr before expiry


class IdentityManager:
    """Manages agent authentication across platforms.

    Rules:
    - Agent may: use API keys, refresh tokens, use existing sessions
    - Agent may NOT: bypass CAPTCHA, KYC, age checks, create Google accounts
    - Human required: new OAuth grants, MFA, legal consent, KYC
    """

    def __init__(self):
        self.sessions: dict[str, AuthSession] = {}
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _load_all(self) -> None:
        for path in CREDENTIALS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                session = AuthSession(
                    platform=data["platform"],
                    auth_type=data["auth_type"],
                    credentials=data.get("credentials", {}),
                    created_at=data.get("created_at", 0),
                    expires_at=data.get("expires_at", 0),
                    refreshed_at=data.get("refreshed_at", 0),
                    human_required=data.get("human_required", False),
                    human_checkpoint_reason=data.get("human_checkpoint_reason", ""),
                )
                self.sessions[session.platform] = session
            except Exception as e:
                log.warning("Failed to load credential %s: %s", path, e)

    def _save(self, platform: str) -> None:
        session = self.sessions.get(platform)
        if not session:
            return
        path = CREDENTIALS_DIR / f"{platform}.json"
        path.write_text(json.dumps({
            "platform": session.platform,
            "auth_type": session.auth_type,
            "credentials": session.credentials,
            "created_at": session.created_at,
            "expires_at": session.expires_at,
            "refreshed_at": session.refreshed_at,
            "human_required": session.human_required,
            "human_checkpoint_reason": session.human_checkpoint_reason,
        }, indent=2))

    def get_session(self, platform: str) -> AuthSession | None:
        return self.sessions.get(platform)

    def has_valid_session(self, platform: str) -> bool:
        session = self.sessions.get(platform)
        return session is not None and session.is_valid

    def register_api_key(self, platform: str, api_key: str,
                         extra: dict | None = None) -> AuthSession:
        """Register a native API key (Taskmarket, Superteam, Clustly, etc.)."""
        creds = {"api_key": api_key}
        if extra:
            creds.update(extra)
        session = AuthSession(
            platform=platform,
            auth_type="api_key",
            credentials=creds,
        )
        self.sessions[platform] = session
        self._save(platform)
        log.info("Registered API key for %s", platform)
        return session

    def register_wallet(self, platform: str, address: str, private_key: str = "") -> AuthSession:
        """Register a crypto wallet (Taskmarket ERC-8004, etc.)."""
        creds = {"address": address}
        if private_key:
            creds["private_key"] = private_key  # encrypted in production
        session = AuthSession(
            platform=platform,
            auth_type="wallet",
            credentials=creds,
        )
        self.sessions[platform] = session
        self._save(platform)
        log.info("Registered wallet for %s: %s", platform, address[:12] + "...")
        return session

    def request_human_auth(self, platform: str, reason: str) -> AuthSession:
        """Mark that this platform needs human intervention.

        The agent CANNOT bypass this. It must prompt the human operator.
        """
        session = AuthSession(
            platform=platform,
            auth_type="human_required",
            credentials={},
            human_required=True,
            human_checkpoint_reason=reason,
        )
        self.sessions[platform] = session
        self._save(platform)
        log.warning("HUMAN AUTH REQUIRED for %s: %s", platform, reason)
        return session

    def complete_human_auth(self, platform: str, auth_type: str,
                            credentials: dict[str, Any]) -> AuthSession:
        """Called by the human operator after completing auth."""
        session = AuthSession(
            platform=platform,
            auth_type=auth_type,
            credentials=credentials,
        )
        self.sessions[platform] = session
        self._save(platform)
        log.info("Human auth completed for %s (%s)", platform, auth_type)
        return session

    def get_api_key(self, platform: str) -> str | None:
        session = self.sessions.get(platform)
        if session and session.auth_type == "api_key":
            return session.credentials.get("api_key")
        return None

    def get_wallet_address(self, platform: str) -> str | None:
        session = self.sessions.get(platform)
        if session and session.auth_type == "wallet":
            return session.credentials.get("address")
        return None

    def needs_human_action(self, platform: str) -> tuple[bool, str]:
        """Check if this platform needs human intervention."""
        session = self.sessions.get(platform)
        if not session:
            return True, "no credentials configured"
        if session.human_required:
            return True, session.human_checkpoint_reason
        if session.needs_refresh:
            return True, "token needs refresh"
        return False, ""

    def status_summary(self) -> dict[str, dict]:
        """Summary of all platform auth status."""
        summary = {}
        for platform, session in self.sessions.items():
            needs_human, reason = self.needs_human_action(platform)
            summary[platform] = {
                "auth_type": session.auth_type,
                "valid": session.is_valid,
                "needs_human": needs_human,
                "reason": reason,
            }
        return summary


# Rules for what the agent can/cannot do
AUTH_RULES = {
    "agent_may": [
        "fill normal forms",
        "click login",
        "use existing authenticated session",
        "use OAuth token",
        "refresh tokens",
        "create an account through an official agent API",
    ],
    "human_required": [
        "CAPTCHA",
        "KYC",
        "age verification",
        "legal agreement requiring human consent",
        "new OAuth permission grant",
        "MFA when the provider requires it",
    ],
}
