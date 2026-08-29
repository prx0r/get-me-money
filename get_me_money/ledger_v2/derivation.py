#!/usr/bin/env python3
"""patala/provenance/derivation.py — Derivation provenance (SLSA-style).

Per newbuild1 §40-41: "Ensure every transformation can export cleanly to PROV.
Internal: DerivationActivity { id, activity_type, inputs[], outputs[], actor_id, software, configuration }"

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from get_me_money.ledger_v2.hashing import uuid7
from patala.db import store


def record_derivation(activity_type: str, inputs: list[dict], outputs: list[dict],
                      actor_id: str = "", software: dict = None,
                      configuration: dict = None) -> str:
    """Record a derivation activity.

    Per newbuildmainspec §69: ExtractionActivity { id, input_observation,
    extractor: { software_id, version, code_digest }, configuration_artifact,
    model_run_id?, outputs[], started_at, completed_at }
    """
    activity_id = f"PTDA_{uuid7()}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    conn = store.get_conn()
    cur = conn.cursor()
    cur.execute(
        '''INSERT INTO derivation_activities
        (id, activity_type, inputs, outputs, actor_id, software, configuration,
         started_at, completed_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
        (activity_id, activity_type, json.dumps(inputs), json.dumps(outputs),
         actor_id, json.dumps(software or {}), json.dumps(configuration or {}),
         now, now, now)
    )
    conn.commit()
    cur.close()
    conn.close()

    return activity_id


def get_derivation(activity_id: str) -> dict | None:
    """Get a derivation activity by ID."""
    conn = store.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM derivation_activities WHERE id = %s", (activity_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return None


def get_derivations_for_entity(entity_id: str) -> list[dict]:
    """Get all derivation activities that produced or consumed an entity."""
    conn = store.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM derivation_activities WHERE %s::text = ANY(inputs::text) OR %s::text = ANY(outputs::text)",
        (entity_id, entity_id)
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if rows else []
    cur.close()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]
