"""Platform adapter contract."""
from __future__ import annotations
import abc
from typing import AsyncIterator
from get_me_money.models import Opportunity, Platform


class BaseAdapter(abc.ABC):
    platform: Platform

    @abc.abstractmethod
    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]: ...

    async def claim(self, opportunity: Opportunity) -> bool:
        return True

    @abc.abstractmethod
    async def submit(self, opportunity: Opportunity, result: dict) -> dict: ...

    @abc.abstractmethod
    async def check_status(self, opportunity: Opportunity) -> dict: ...

    async def health_check(self) -> bool:
        return True
