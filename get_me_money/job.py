"""Canonical Job — one portable job object, many discovery surfaces, one settlement.

This is the primitive that makes Moltwork the job layer, not another marketplace.

A Job is created once, can be advertised on multiple venues,
but settles through exactly one venue.

Flow:
  1. Buyer creates canonical job (mw:job:abc)
  2. Moltwork distributes to venues (taskmarket, moltjobs, native)
  3. Each venue gets its own binding (venue_job_id, venue_url)
  4. Exactly one venue handles settlement
  5. Worker acts on the job through WorkerKit
  6. Moltwork observes the outcome
  7. Receipt + capability evidence recorded

The job carries:
  - canonical spec (what must be done)
  - venue bindings (where it's listed)
  - settlement authority (who pays)
  - state machine (funded → open → submitted → awarded → paid)
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


class JobStatus(str, Enum):
    DRAFT = "draft"
    FUNDED = "funded"
    OPEN = "open"
    SUBMITTED = "submitted"
    AWARDED = "awarded"
    PAID = "paid"
    CANCELLED = "cancelled"


@dataclass
class VenueBinding:
    """A job's presence on a specific marketplace."""
    venue: str = ""           # "taskmarket", "moltjobs", "moltwork", etc.
    venue_job_id: str = ""    # platform-specific ID
    venue_url: str = ""       # link to the job on the venue
    settlement: str = "external"  # "external" or "native"
    funded: bool = False
    created_at: float = 0.0


@dataclass
class CanonicalJob:
    """One portable job object. The core primitive for the job layer."""
    id: str = field(default_factory=lambda: f"mw:job:{uuid.uuid4().hex[:12]}")

    # Spec
    title: str = ""
    description: str = ""
    reward: float = 0.0
    currency: str = "USDC"
    category: str = ""
    skills_required: list[str] = field(default_factory=list)
    hard_requirements: list[str] = field(default_factory=list)
    scoring: dict[str, float] = field(default_factory=dict)
    deadline: str = ""

    # State
    status: JobStatus = JobStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # Venue bindings
    venues: list[VenueBinding] = field(default_factory=list)

    # Settlement
    settlement_venue: str = ""  # which venue handles payment
    settlement_ref: str = ""    # venue-specific settlement reference

    # Metadata
    buyer_id: str = ""
    buyer_name: str = ""
    tags: list[str] = field(default_factory=list)

    def spec_hash(self) -> str:
        """Content hash of the job specification."""
        raw = json.dumps({
            "title": self.title,
            "description": self.description[:2000],
            "reward": self.reward,
            "skills_required": self.skills_required,
            "hard_requirements": self.hard_requirements,
            "scoring": self.scoring,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def add_venue(self, venue: str, venue_job_id: str, venue_url: str = "",
                  settlement: str = "external") -> VenueBinding:
        """Bind this job to a marketplace venue."""
        binding = VenueBinding(
            venue=venue, venue_job_id=venue_job_id,
            venue_url=venue_url, settlement=settlement,
            created_at=time.time(),
        )
        self.venues.append(binding)
        if not self.settlement_venue and settlement == "external":
            self.settlement_venue = venue
            self.settlement_ref = venue_job_id
        self.updated_at = time.time()
        return binding

    def get_binding(self, venue: str) -> VenueBinding | None:
        """Get the binding for a specific venue."""
        for v in self.venues:
            if v.venue == venue:
                return v
        return None

    def active_venues(self) -> list[VenueBinding]:
        """Get all venues where this job is listed."""
        return [v for v in self.venues if v.funded or v.venue == self.settlement_venue]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description[:500],
            "reward": self.reward,
            "currency": self.currency,
            "category": self.category,
            "skills_required": self.skills_required,
            "hard_requirements": self.hard_requirements,
            "scoring": self.scoring,
            "deadline": self.deadline,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "venues": [asdict(v) for v in self.venues],
            "settlement_venue": self.settlement_venue,
            "settlement_ref": self.settlement_ref,
            "buyer_id": self.buyer_id,
            "spec_hash": self.spec_hash(),
        }

    def to_jobspec_dict(self) -> dict:
        """Convert to JobSpec format for WorkerKit."""
        return {
            "objective": self.title,
            "hard_requirements": self.hard_requirements or [self.description[:200]],
            "scoring": self.scoring or {"completeness": 0.5, "quality": 0.5},
            "automatic_rejection": ["Does not address the task", "Empty submission"],
            "evidence_required": ["artifact_files"],
            "deliverable_format": "mixed",
        }

    def save(self, path: Path):
        """Save job to disk."""
        path.mkdir(parents=True, exist_ok=True)
        (path / "job.json").write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> CanonicalJob:
        """Load job from disk."""
        data = json.loads((path / "job.json").read_text())
        job = cls()
        for k, v in data.items():
            if k == "venues":
                job.venues = [VenueBinding(**vb) for vb in v]
            elif k == "status":
                job.status = JobStatus(v)
            elif hasattr(job, k):
                setattr(job, k, v)
        return job


class JobRouter:
    """Routes a canonical job to venues.

    The router decides where to list a job and how to distribute it.
    """

    def __init__(self):
        self._venues: dict[str, Any] = {}

    def register_venue(self, name: str, adapter: Any):
        """Register a venue adapter."""
        self._venues[name] = adapter

    async def distribute(self, job: CanonicalJob, venues: list[str] | None = None) -> list[VenueBinding]:
        """Distribute a job to one or more venues."""
        target_venues = venues or list(self._venues.keys())
        bindings = []

        for venue_name in target_venues:
            adapter = self._venues.get(venue_name)
            if not adapter:
                continue

            try:
                # Post to the venue
                venue_job_id = await adapter.post_job(job)
                binding = job.add_venue(
                    venue=venue_name,
                    venue_job_id=venue_job_id,
                    settlement="external",
                )
                bindings.append(binding)
            except Exception as e:
                # Venue failed, continue with others
                pass

        return bindings

    async def observe_outcome(self, job: CanonicalJob) -> dict | None:
        """Check settlement venue for job outcome."""
        if not job.settlement_venue or not job.settlement_ref:
            return None

        adapter = self._venues.get(job.settlement_venue)
        if not adapter:
            return None

        try:
            return await adapter.check_status(job.settlement_ref)
        except Exception:
            return None
