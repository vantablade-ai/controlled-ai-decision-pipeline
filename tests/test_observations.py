from app.core.observations import derive_observations
from app.core.snapshot import make_snapshot
from app.models import EvidenceRequest


def test_observations_are_deterministic(evidence):
    a = derive_observations(EvidenceRequest.model_validate(evidence))
    b = derive_observations(EvidenceRequest.model_validate(evidence))
    assert a == b
    assert {o.code for o in a[0]} >= {"REPEATED_EVENT", "HIGH_FAILURE_RATE", "RECURRING_MANUAL_WORK"}


def test_missing_evidence_detected():
    observations, _ = derive_observations(EvidenceRequest(subject="x", missing_information=["sample size"]))
    assert observations[0].code in {"REQUIRED_INFORMATION_MISSING", "NO_MEASURED_EVIDENCE"}


def test_hash_stable_and_changes_with_evidence(evidence):
    req = EvidenceRequest.model_validate(evidence)
    assert make_snapshot(req).snapshot_hash == make_snapshot(req).snapshot_hash
    changed = {**evidence, "subject": "Different issue"}
    assert (
        make_snapshot(EvidenceRequest.model_validate(changed)).snapshot_hash
        != make_snapshot(req).snapshot_hash
    )


def test_hash_ignores_input_json_key_order(evidence):
    reversed_fields = dict(reversed(list(evidence.items())))
    assert (
        make_snapshot(EvidenceRequest.model_validate(evidence)).snapshot_hash
        == make_snapshot(EvidenceRequest.model_validate(reversed_fields)).snapshot_hash
    )
