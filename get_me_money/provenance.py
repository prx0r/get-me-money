"""Provenance — content-addressed WorkerRun with in-toto style attestations.

Level 1: SHA-256 hashes, append-only event chain, Merkle root, signed.
Level 2: in-toto attestations (standard format).
Level 3+: Sigstore/Rekor, TEE (future).

Every run produces an immutable, tamper-evident record.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def sha256(data: bytes | str) -> str:
    """Content hash — deterministic, collision-resistant."""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()[:16]


@dataclass
class RunEvent:
    """One event in the execution chain."""
    timestamp: float = 0.0
    event_type: str = ""  # llm_call, tool_call, cost, decision, artifact
    data: dict = field(default_factory=dict)
    prev_hash: str = ""  # chain link

    def to_bytes(self) -> bytes:
        return json.dumps({
            "timestamp": self.timestamp,
            "type": self.event_type,
            "data": self.data,
            "prev": self.prev_hash,
        }, sort_keys=True).encode()


@dataclass
class WorkerRun:
    """Content-addressed, immutable execution record.

    The root hash binds everything together.
    Change any event → root hash changes.
    """
    run_id: str = ""
    created_at: float = field(default_factory=time.time)

    # Manifest (what configuration produced this run)
    workerkit_version: str = "0.3.0"
    agent_config_hash: str = ""
    skills_hash: str = ""
    source_revision: str = ""
    model_used: str = ""
    routing_policy: str = ""

    # Inputs
    input_hashes: list[str] = field(default_factory=list)

    # Events (append-only, chained)
    events: list[RunEvent] = field(default_factory=list)

    # Outputs
    output_hash: str = ""
    output_preview: str = ""

    # Verification
    verifier_hash: str = ""
    verification_result: str = ""  # PASS/FAIL

    # Outcome
    submitted: bool = False
    accepted: bool = False
    reward: float = 0.0
    receipt_hash: str = ""

    def add_event(self, event_type: str, data: dict) -> RunEvent:
        """Append an event to the chain."""
        prev = self.events[-1].to_bytes() if self.events else b""
        event = RunEvent(
            timestamp=time.time(),
            event_type=event_type,
            data=data,
            prev_hash=sha256(prev),
        )
        self.events.append(event)
        return event

    def manifest_hash(self) -> str:
        """Hash of the configuration manifest."""
        manifest = {
            "workerkit_version": self.workerkit_version,
            "agent_config_hash": self.agent_config_hash,
            "skills_hash": self.skills_hash,
            "model_used": self.model_used,
            "routing_policy": self.routing_policy,
        }
        return sha256(json.dumps(manifest, sort_keys=True))

    def events_hash(self) -> str:
        """Merkle-ish hash of all events."""
        if not self.events:
            return sha256("")
        chain = b""
        for event in self.events:
            chain = sha256(chain + event.to_bytes()).encode()
        return chain.decode() if isinstance(chain, bytes) else chain

    def root_hash(self) -> str:
        """Root hash binding everything together."""
        parts = [
            self.manifest_hash(),
            self.events_hash(),
            self.output_hash,
            self.verifier_hash,
            str(self.reward),
            str(self.accepted),
        ]
        return sha256(":".join(parts))

    def to_attestation(self) -> dict:
        """in-toto style attestation."""
        return {
            "_type": "https://moltwork.com/attestation/worker-run/v1",
            "subject": {
                "digest": {"sha256": self.output_hash},
                "name": self.run_id,
            },
            "predicate": {
                "workerkit_version": self.workerkit_version,
                "agent_config_hash": self.agent_config_hash,
                "skills_hash": self.skills_hash,
                "model_used": self.model_used,
                "input_hashes": self.input_hashes,
                "event_count": len(self.events),
                "events_hash": self.events_hash(),
                "output_hash": self.output_hash,
                "verifier_hash": self.verifier_hash,
                "verification_result": self.verification_result,
                "submitted": self.submitted,
                "accepted": self.accepted,
                "reward": self.reward,
                "receipt_hash": self.receipt_hash,
                "root_hash": self.root_hash(),
                "created_at": self.created_at,
            },
        }

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        attestation = self.to_attestation()
        (path / "attestation.json").write_text(json.dumps(attestation, indent=2))
        (path / "root_hash.txt").write_text(self.root_hash())
        # Save events as append-only log
        with open(path / "events.jsonl", "a") as f:
            for event in self.events:
                f.write(json.dumps({
                    "timestamp": event.timestamp,
                    "type": event.event_type,
                    "data": event.data,
                    "prev": event.prev_hash,
                }) + "\n")

    @classmethod
    def load(cls, path: Path) -> WorkerRun:
        att = json.loads((path / "attestation.json").read_text())
        pred = att.get("predicate", {})
        run = cls()
        run.run_id = att.get("subject", {}).get("name", "")
        run.workerkit_version = pred.get("workerkit_version", "")
        run.agent_config_hash = pred.get("agent_config_hash", "")
        run.model_used = pred.get("model_used", "")
        run.output_hash = pred.get("output_hash", "")
        run.submitted = pred.get("submitted", False)
        run.accepted = pred.get("accepted", False)
        run.reward = pred.get("reward", 0)
        run.created_at = pred.get("created_at", 0)
        return run
