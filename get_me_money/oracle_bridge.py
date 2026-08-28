"""Oracle bridge — sends SubmissionRuns to the oracle as observations.

Every completed job feeds market intelligence.
"""
from __future__ import annotations

import json
import logging
import time

log = logging.getLogger(__name__)


async def submit_to_oracle(run_data: dict, oracle_url: str = "http://localhost:8788") -> bool:
    """Submit a SubmissionRun to the oracle as an observation."""
    import urllib.request

    observation = {
        "source": "workerkit",
        "source_id": run_data.get("id", ""),
        "event_type": "opportunity_observed",
        "payload": {
            "title": run_data.get("task_title", ""),
            "reward_usd": run_data.get("task_reward", 0),
            "status": run_data.get("external_status", "pending"),
            "judge_score": run_data.get("judge_score", 0),
            "cost": run_data.get("total_cost", 0),
            "strategy": run_data.get("strategy_version", "default"),
            "skills": run_data.get("skills_used", []),
        },
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    try:
        data = json.dumps(observation).encode()
        req = urllib.request.Request(
            f"{oracle_url}/v1/observations",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        log.warning(f"Oracle submission failed: {e}")
        return False
