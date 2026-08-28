"""Platform adapter base class."""

from __future__ import annotations

import abc
from typing import AsyncIterator

from get_me_money.models import Opportunity, Platform


class BaseAdapter(abc.ABC):
    """All platform adapters implement this."""

    platform: Platform

    @abc.abstractmethod
    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        """Yield open opportunities from this platform."""
        ...

    @abc.abstractmethod
    async def claim(self, opportunity: Opportunity) -> bool:
        """Attempt to claim/apply for an opportunity. Returns True on success."""
        ...

    @abc.abstractmethod
    async def submit(self, opportunity: Opportunity, result: dict) -> bool:
        """Submit completed work. Returns True on success."""
        ...

    @abc.abstractmethod
    async def check_status(self, opportunity: Opportunity) -> dict:
        """Check payment / completion status."""
        ...

    async def health_check(self) -> bool:
        """Optional: can we reach this platform right now?"""
        return True
