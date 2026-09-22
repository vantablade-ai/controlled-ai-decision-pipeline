from app.core.policy import apply_policy
from app.models import AuthorityMode, DecisionStatus, EvidenceQuality, ProviderDecisionPayload


def payload(**kwargs):
    fields = {
        "status": "RECOMMEND",
        "confidence": "HIGH",
        "evidence_quality": "STRONG",
        "rationale": "Supported.",
        "recommended_action": "Queue review",
        "action_class": "CREATE_REVIEW_TICKET",
        "requested_authority": "AUTO_SAFE",
    }
    fields.update(kwargs)
    return ProviderDecisionPayload(**fields)


def test_insufficient_and_partial_quality_cap_authority():
    result = apply_policy(
        payload(), deterministic_quality=EvidenceQuality.INSUFFICIENT, deterministic_conflicts=[]
    )
    assert result[0] == AuthorityMode.HUMAN_ONLY and result[3] == DecisionStatus.NOT_ANALYZED
    result = apply_policy(
        payload(), deterministic_quality=EvidenceQuality.PARTIAL, deterministic_conflicts=[]
    )
    assert result[0] == AuthorityMode.APPROVAL_REQUIRED


def test_strong_evidence_and_allowlisted_action_can_be_auto_safe():
    result = apply_policy(payload(), deterministic_quality=EvidenceQuality.STRONG, deterministic_conflicts=[])
    assert result[0] == AuthorityMode.AUTO_SAFE


def test_no_action_is_never_executable():
    result = apply_policy(
        payload(status="NO_ACTION"),
        deterministic_quality=EvidenceQuality.STRONG,
        deterministic_conflicts=[],
    )
    assert result[1].value == "NON_ACTIONABLE"


def test_risky_action_remains_human_only():
    result = apply_policy(
        payload(action_class="CHANGE_PRODUCTION"),
        deterministic_quality=EvidenceQuality.STRONG,
        deterministic_conflicts=[],
    )
    assert result[0] == AuthorityMode.HUMAN_ONLY


def test_conflict_forces_investigation():
    result = apply_policy(
        payload(),
        deterministic_quality=EvidenceQuality.CONFLICTING,
        deterministic_conflicts=["signal conflict"],
    )
    assert result[3] == DecisionStatus.INVESTIGATE and result[0] == AuthorityMode.HUMAN_ONLY
