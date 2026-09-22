import hashlib
import json

from app.core.observations import derive_observations
from app.models import EvidenceRequest, EvidenceSnapshot


def canonical_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_snapshot(request: EvidenceRequest) -> EvidenceSnapshot:
    observations, conflicts = derive_observations(request)
    missing_information = list(request.missing_information)
    if not request.evidence_sources:
        missing_information.append("evidence source references")
    body = {
        "schema_version": "1.0.0",
        "request": request.model_dump(mode="json"),
        "observations": [item.model_dump(mode="json") for item in observations],
        "conflicts": conflicts,
        "missing_information": sorted(set(missing_information)),
    }
    digest = hashlib.sha256(canonical_json(body).encode()).hexdigest()
    return EvidenceSnapshot(**body, snapshot_hash=digest)
