import json
import sqlite3
from pathlib import Path

from app.models import Decision


class AuditRepository:
    def __init__(self, path: str = "decision_audit.sqlite3"):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(Path(__file__).parents[2].joinpath("schema.sql").read_text())

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, decision: Decision, snapshot: dict, provider_output: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO decisions (decision_id, snapshot_hash, snapshot_json, observations_json, provider, provider_output_json, decision_json, authority_mode, approval_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    decision.decision_id,
                    decision.snapshot_hash,
                    json.dumps(snapshot, sort_keys=True),
                    json.dumps(snapshot.get("observations", []), sort_keys=True),
                    decision.provider,
                    json.dumps(provider_output, sort_keys=True),
                    decision.model_dump_json(),
                    decision.authority_mode.value,
                    decision.approval_status.value,
                    decision.created_at.isoformat(),
                ),
            )

    def get(self, decision_id: str) -> Decision | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT decision_json FROM decisions WHERE decision_id=?", (decision_id,)
            ).fetchone()
        return Decision.model_validate_json(row[0]) if row else None

    def get_snapshot(self, decision_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT snapshot_json FROM decisions WHERE decision_id=?", (decision_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, limit: int = 100) -> list[Decision]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT decision_json FROM decisions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [Decision.model_validate_json(row[0]) for row in rows]

    def transition(self, decision_id: str, decision: Decision) -> None:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE decisions SET decision_json=?, approval_status=? WHERE decision_id=? AND approval_status='PENDING'",
                (decision.model_dump_json(), decision.approval_status.value, decision_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("approval transition is no longer available")
