from enum import StrEnum

from app.models import (
    AuthorityMode,
    Confidence,
    DecisionStatus,
    EvidenceQuality,
    EvidenceSnapshot,
    ProviderDecisionPayload,
)


class MockScenario(StrEnum):
    VALID = "valid"
    INVALID_SCHEMA = "invalid_schema"
    ERROR = "error"
    LOW_CONFIDENCE = "low_confidence"
    CONFLICTING = "conflicting"
    NOT_ANALYZED = "not_analyzed"


class MockProvider:
    name = "mock"
    model = "deterministic-v1"

    def __init__(self, scenario: MockScenario = MockScenario.VALID):
        self.scenario = scenario

    def analyze(self, snapshot: EvidenceSnapshot) -> ProviderDecisionPayload:
        if self.scenario == MockScenario.ERROR:
            raise RuntimeError("mock provider unavailable")
        if self.scenario == MockScenario.INVALID_SCHEMA:
            return ProviderDecisionPayload.model_validate({"status": "MADE_UP"})
        quality = (
            EvidenceQuality.STRONG
            if len(snapshot.observations) >= 2 and not snapshot.missing_information
            else EvidenceQuality.PARTIAL
        )
        status = DecisionStatus.RECOMMEND if quality == EvidenceQuality.STRONG else DecisionStatus.INVESTIGATE
        conf = Confidence.HIGH if quality == EvidenceQuality.STRONG else Confidence.MEDIUM
        if self.scenario == MockScenario.LOW_CONFIDENCE:
            conf = Confidence.LOW
        if self.scenario == MockScenario.CONFLICTING:
            quality, status = EvidenceQuality.CONFLICTING, DecisionStatus.INVESTIGATE
        if self.scenario == MockScenario.NOT_ANALYZED:
            quality, status = EvidenceQuality.INSUFFICIENT, DecisionStatus.NOT_ANALYZED
        refs = sorted({ref for obs in snapshot.observations for ref in obs.evidence_references})
        return ProviderDecisionPayload(
            status=status,
            confidence=conf,
            evidence_quality=quality,
            rationale="The recommendation is bounded to the supplied evidence and deterministic observations.",
            evidence_references=refs,
            limitations=["Synthetic demonstration; not an operational diagnosis."],
            conflicts=snapshot.conflicts,
            missing_information=snapshot.missing_information,
            recommended_action="Queue a human review of the observed workflow.",
            action_class="CREATE_REVIEW_TICKET",
            requested_authority=AuthorityMode.APPROVAL_REQUIRED,
        )
