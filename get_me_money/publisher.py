"""Publisher — upload artifacts to marketplaces.

Unified interface for publishing finished work to multiple venues:
  - Moltwork (repute server)
  - Taskmarket
  - Superteam
  - Any MCP-compatible marketplace

Usage:
    publisher = Publisher(config)
    result = await publisher.publish(
        title="Competitive Intelligence Report",
        content=open("SUBMISSION.md").read(),
        artifacts=["report.pdf", "data.csv"],
        price=5.0,
        venues=["moltwork", "taskmarket"]
    )
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class PublishResult:
    venue: str = ""
    success: bool = False
    url: str = ""
    id: str = ""
    error: str = ""


class Publisher:
    """Publish artifacts to multiple marketplaces."""

    def __init__(self, config=None):
        self.config = config

    async def publish(
        self,
        title: str,
        content: str,
        artifacts: list[str] | None = None,
        price: float = 0.0,
        category: str = "report",
        venues: list[str] | None = None,
    ) -> list[PublishResult]:
        """Publish to one or more venues."""
        results = []

        for venue in (venues or ["moltwork"]):
            try:
                if venue == "moltwork":
                    r = await self._publish_moltwork(title, content, artifacts, price, category)
                elif venue == "taskmarket":
                    r = await self._publish_taskmarket(title, content, artifacts, price)
                elif venue == "moltjobs":
                    r = await self._publish_moltjobs(title, content, artifacts, price)
                elif venue == "superteam":
                    r = await self._publish_superteam(title, content, artifacts, price)
                else:
                    r = PublishResult(venue=venue, error=f"Unknown venue: {venue}")
                results.append(r)
            except Exception as e:
                results.append(PublishResult(venue=venue, error=str(e)))

        return results

    async def _publish_moltwork(self, title, content, artifacts, price, category) -> PublishResult:
        """Publish to Moltwork (repute server)."""
        import urllib.request

        try:
            data = json.dumps({
                "title": title,
                "abstract": content[:500],
                "body": content,
                "total_price": price,
                "currency": "USDC",
                "category": category,
                "license": "derivative-commercial",
            }).encode()

            req = urllib.request.Request(
                "http://localhost:8788/api/products",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                return PublishResult(
                    venue="moltwork",
                    success=True,
                    id=result.get("product_id", ""),
                    url=f"http://localhost:8788/api/products/{result.get('product_id', '')}",
                )
        except Exception as e:
            return PublishResult(venue="moltwork", error=str(e))

    async def _publish_taskmarket(self, title, content, artifacts, price) -> PublishResult:
        """Publish to Taskmarket (via CLI)."""
        import subprocess

        # Create a post file
        post_dir = Path("/tmp/moltwork-publish")
        post_dir.mkdir(exist_ok=True)
        post_file = post_dir / "post.md"
        post_file.write_text(f"# {title}\n\n{content}")

        try:
            result = subprocess.run(
                ["taskmarket", "task", "create", "--file", str(post_file)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return PublishResult(
                    venue="taskmarket",
                    success=True,
                    id=data.get("taskId", ""),
                    url=f"https://taskmarket.dev/task/{data.get('taskId', '')}",
                )
            else:
                return PublishResult(venue="taskmarket", error=result.stderr[:200])
        except Exception as e:
            return PublishResult(venue="taskmarket", error=str(e))

    async def _publish_moltjobs(self, title, content, artifacts, price) -> PublishResult:
        """Publish to MoltJobs."""
        # Placeholder — MoltJobs has API but needs auth
        return PublishResult(venue="moltjobs", error="Not implemented — needs API key")

    async def _publish_superteam(self, title, content, artifacts, price) -> PublishResult:
        """Publish to Superteam."""
        # Placeholder — Superteam has API but needs auth
        return PublishResult(venue="superteam", error="Not implemented — needs API key")
