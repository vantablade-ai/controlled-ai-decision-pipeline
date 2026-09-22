CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    snapshot_hash TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    observations_json TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_output_json TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    authority_mode TEXT NOT NULL CHECK (authority_mode IN ('AUTO_SAFE','APPROVAL_REQUIRED','HUMAN_ONLY')),
    approval_status TEXT NOT NULL CHECK (approval_status IN ('NOT_REQUIRED','PENDING','APPROVED','REJECTED')),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS decisions_created_at_idx ON decisions(created_at);
