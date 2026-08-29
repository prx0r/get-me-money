"""Canonical event ledger — append-only, content-addressed.

From Wiggly, adapted for SQLite.
Events are truth. Tables are projections.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from get_me_money.ledger_v2.hashing import uuid7, canonical_jcs_hash


class CanonicalEventStore:
    """Append-only event ledger. Events are truth."""

    def __init__(self, db_path: str = "data/events.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                cursor INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                event_type TEXT,
                entity_ids TEXT,
                schema_uri TEXT,
                actor_id TEXT,
                occurred_at TEXT,
                recorded_at TEXT,
                payload TEXT,
                payload_digest TEXT,
                derivation_refs TEXT,
                run_id TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    def append(self, event_type: str, payload: dict, entity_ids: list = None,
               actor_id: str = None, run_id: str = None) -> dict:
        """Append event. Never mutate existing events."""
        conn = self._conn()
        event_id = f"evt_{uuid7()[:16]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload_digest = json.dumps(canonical_jcs_hash(payload))

        conn.execute("""
            INSERT INTO events (event_id, event_type, entity_ids, schema_uri,
                actor_id, occurred_at, recorded_at, payload, payload_digest,
                derivation_refs, run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_id, event_type, json.dumps(entity_ids or []),
              "https://moltwork.com/schemas/v1/event.json",
              actor_id, now, now, json.dumps(payload),
              payload_digest, json.dumps([]), run_id))
        conn.commit()
        conn.close()
        return {"event_id": event_id, "recorded_at": now}

    def get_events_since(self, cursor: int, limit: int = 100) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM events WHERE cursor > ? ORDER BY cursor LIMIT ?",
            (cursor, limit)
        ).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM events LIMIT 0").description]
        conn.close()
        return [dict(zip(cols, r)) for r in rows]

    def count(self) -> int:
        conn = self._conn()
        n = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        conn.close()
        return n
