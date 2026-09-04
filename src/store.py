"""SQLite persistence + the hidden-downtime -> verified-action metric."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    finding_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT,
    cause        TEXT,
    cause_label  TEXT,
    context      TEXT,
    events       INTEGER,
    recoverable_min REAL,
    support      REAL,
    confidence   REAL,
    lift         REAL,
    impact       REAL,
    example_notes TEXT,
    plain_language TEXT,
    suggested_action TEXT
);
CREATE TABLE IF NOT EXISTS verifications (
    finding_id   INTEGER PRIMARY KEY,
    decision     TEXT,          -- 'verified' | 'rejected'
    verified_by  TEXT,
    action_owner TEXT,
    action_text  TEXT,
    decided_at   TEXT,
    FOREIGN KEY(finding_id) REFERENCES findings(finding_id)
);
CREATE TABLE IF NOT EXISTS metrics (
    run_id       TEXT PRIMARY KEY,
    ts           TEXT,
    micro_minutes_total REAL,
    minutes_attributed REAL,
    pct_attributed REAL,
    causes_surfaced INTEGER
);
"""


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        with self._conn() as c:
            c.executescript(SCHEMA)

    def reset(self):
        with self._conn() as c:
            c.executescript(
                "DROP TABLE IF EXISTS findings;"
                "DROP TABLE IF EXISTS verifications;"
                "DROP TABLE IF EXISTS metrics;"
            )
            c.executescript(SCHEMA)

    # --- writes ---
    def save_findings(self, run_id: str, findings: list[dict]) -> list[int]:
        ids = []
        with self._conn() as c:
            for f in findings:
                cur = c.execute(
                    """INSERT INTO findings (run_id, cause, cause_label, context, events,
                       recoverable_min, support, confidence, lift, impact, example_notes,
                       plain_language, suggested_action)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run_id, f["cause"], f["cause_label"], f["context"], f["events"],
                     f["recoverable_min"], f["support"], f["confidence"], f["lift"],
                     f["impact"], json.dumps(f["example_notes"]), f["plain_language"],
                     f["suggested_action"]),
                )
                ids.append(cur.lastrowid)
        return ids

    def save_metrics(self, run_id: str, m: dict):
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO metrics (run_id, ts, micro_minutes_total,
                   minutes_attributed, pct_attributed, causes_surfaced)
                   VALUES (?,?,?,?,?,?)""",
                (run_id, _now(), m["micro_minutes_total"],
                 m["minutes_attributed"], m["pct_attributed"], m["causes_surfaced"]),
            )

    def verify(self, finding_id: int, decision: str, verified_by: str = "",
               action_owner: str = "", action_text: str = "") -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO verifications
                   (finding_id, decision, verified_by, action_owner, action_text, decided_at)
                   VALUES (?,?,?,?,?,?)""",
                (finding_id, decision, verified_by, action_owner, action_text,
                 _now()),
            )

    # --- reads ---
    def get_findings(self, run_id: str | None = None) -> list[dict]:
        q = "SELECT * FROM findings"
        args = ()
        if run_id:
            q += " WHERE run_id = ?"
            args = (run_id,)
        q += " ORDER BY impact DESC"
        with self._conn() as c:
            rows = [dict(r) for r in c.execute(q, args).fetchall()]
        # attach verification status
        with self._conn() as c:
            vers = {r["finding_id"]: dict(r)
                    for r in c.execute("SELECT * FROM verifications").fetchall()}
        for i, r in enumerate(rows, 1):
            r["example_notes"] = json.loads(r["example_notes"] or "[]")
            r["rank"] = i  # rows are ordered by impact desc
            v = vers.get(r["finding_id"])
            r["verification"] = v
        return rows

    def latest_run_id(self) -> str | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT run_id FROM metrics ORDER BY ts DESC LIMIT 1").fetchone()
        return row["run_id"] if row else None

    def conversion_metric(self) -> dict:
        """Hidden downtime -> verified corrective actions."""
        with self._conn() as c:
            findings = [dict(r) for r in c.execute("SELECT * FROM findings").fetchall()]
            vers = {r["finding_id"]: dict(r)
                    for r in c.execute("SELECT * FROM verifications").fetchall()}
        verified = [f for f in findings if vers.get(f["finding_id"], {}).get("decision") == "verified"]
        return {
            "total_findings": len(findings),
            "verified_actions": len(verified),
            "verified_recoverable_min": round(sum(f["recoverable_min"] for f in verified), 1),
            "total_recoverable_min": round(sum(f["recoverable_min"] for f in findings), 1),
        }
