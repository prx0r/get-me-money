"""Moltwork adapter — turns completed external work into earning inventory.

When get-me-money finishes a job on any platform, this adapter:
1. Imports the work as a Moltwork Product (if license permits)
2. Creates a Receipt proving the work happened
3. Builds capability evidence for the agent
4. Enables future sales of the work

The agent doesn't "join a marketplace" — it gets economic capability.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import AsyncIterator

import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory, Attempt, Outcome
from get_me_money.platforms import BaseAdapter


class MoltworkAdapter:
    """Posts completed work to Moltwork as Products + Receipts.

    This is NOT a job-source adapter (we don't scan Moltwork for jobs).
    It's a post-job-hook adapter: after completing work elsewhere,
    we import it into Moltwork to build reputation and enable resale.
    """

    def __init__(self, base_url: str = "http://localhost:8788", worker_id: str = ""):
        self.base_url = base_url.rstrip("/")
        self.worker_id = worker_id
        self.client = httpx.Client(timeout=30)

    def _post(self, path: str, body: dict) -> dict:
        try:
            r = self.client.post(f"{self.base_url}{path}", json=body)
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get(self, path: str) -> dict:
        try:
            r = self.client.get(f"{self.base_url}{path}")
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def import_completed_work(self, attempt: Attempt, result_content: str = "",
                               license: str = "reuse permitted") -> dict:
        """Import a completed job as a Moltwork Product.

        Called after attempt succeeds or is rejected (work was still done).
        Only imports if:
        - result_content is non-empty
        - license permits reuse
        - work is substantial enough to be useful
        """
        if not result_content or len(result_content) < 100:
            return {"ok": False, "reason": "content_too_short"}

        if license not in ("reuse permitted", "cc-by"):
            return {"ok": False, "reason": f"license_not_reusable: {license}"}

        # Auto-suggest price based on category
        price = self._suggest_price(attempt)

        # Import as Product
        result = self._post("/api/import", {
            "title": attempt.title,
            "text": result_content,
            "worker_id": self.worker_id,
            "source": attempt.platform.value,
            "source_job_id": attempt.external_id,
            "category": self._category_to_moltwork(attempt.metadata.get("category", "unknown")),
            "tags": attempt.metadata.get("skills_used", []),
            "price": price,
            "license": license,
        })

        # Create receipt
        if result.get("ok"):
            product_id = result["product"]["id"]
            self._create_receipt(attempt, product_id)

        return result

    def _create_receipt(self, attempt: Attempt, product_id: str = "") -> dict:
        """Create a work receipt — proof the agent did real work."""
        return self._post("/api/receipts", {
            "agent_id": self.worker_id,
            "job_source": attempt.platform.value,
            "job_id": attempt.external_id,
            "capability": attempt.metadata.get("category", "general"),
            "input_hash": hashlib.sha256(attempt.title.encode()).hexdigest()[:16],
            "output_hash": hashlib.sha256((attempt.submission_url or attempt.title).encode()).hexdigest()[:16],
            "output_preview": attempt.title[:200],
            "status": attempt.outcome.value,
            "amount_earned": attempt.reward,
            "currency": "USDC",
            "buyer_id": "",
        })

    def create_capability(self, category: str, description: str = "") -> dict:
        """Register a capability the agent has demonstrated."""
        return self._post("/api/capabilities", {
            "agent_id": self.worker_id,
            "name": category,
            "description": description or f"Agent can perform {category} work",
        })

    def list_products(self) -> dict:
        """Check what Products the agent has published."""
        return self._get("/api/products")

    def get_reputation(self) -> dict:
        """Check the agent's Moltwork reputation."""
        return self._get(f"/api/reputation/{self.worker_id}")

    def search_demand(self) -> dict:
        """See what buyers are looking for."""
        return self._get("/api/demand/trending")

    def _suggest_price(self, attempt: Attempt) -> float:
        """Suggest price based on category and reward."""
        # Base price from external reward, discounted for resale
        base = attempt.reward * 0.3  # 30% of original job value
        # Category adjustments
        category = attempt.metadata.get("category", "unknown")
        multipliers = {
            "research": 1.0,
            "code_fix": 0.8,
            "data_extraction": 1.2,
            "content": 0.6,
            "api_work": 0.9,
        }
        return round(base * multipliers.get(category, 0.8), 4)

    def _category_to_moltwork(self, category: str) -> str:
        """Map get-me-money categories to Moltwork categories."""
        mapping = {
            "research": "research",
            "code_fix": "code",
            "code_feature": "code",
            "data_extraction": "data",
            "content": "content",
            "api_work": "code",
            "documentation": "content",
            "testing": "code",
            "design": "content",
        }
        return mapping.get(category, "research")
