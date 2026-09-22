import uuid
from datetime import UTC, datetime

from app.core.policy import apply_policy
from app.core.snapshot import make_snapshot
from app.models import (
    Actionability,
    ApprovalStatus,
    AuthorityMode,
    Confidence,
    Decision,
    DecisionStatus,
    EvidenceQuality,
    EvidenceRequest,
    ProviderDecisionPayload,
)
from app.providers.mock import MockProvider


class ReasoningService:
    def __init__(self, provider=None, repository=None):
        self.provider = provider or MockProvider()
        self.repository = repository

    def create(self, request: EvidenceRequest) -> Decision:
        snapshot = make_snapshot(request)
        provider_output = {}
        try:
            payload = self.provider.analyze(snapshot)
            if not isinstance(payload, ProviderDecisionPayload):
                payload = ProviderDecisionPayload.model_validate(payload)
            valid_references = set(request.evidence_sources)
            valid_references.update(item.source_id for item in request.observed_events)
            valid_references.update(item.source_id for item in request.metrics)
            if not set(payload.evidence_references).issubset(valid_references):
                raise ValueError("provider referenced evidence outside the snapshot")
            provider_output = payload.model_dump(mode="json")
            has_measured_evidence = bool(
                request.observed_events or request.metrics or request.known_failures or request.manual_steps
            )
            deterministic_quality = (
                EvidenceQuality.INSUFFICIENT
                if snapshot.missing_information or not request.evidence_sources or not has_measured_evidence
                else EvidenceQuality.PARTIAL
            )
            if snapshot.conflicts:
                deterministic_quality = EvidenceQuality.CONFLICTING
            elif (
                len(snapshot.observations) >= 2
                and request.evidence_sources
                and not snapshot.missing_information
            ):
                deterministic_quality = EvidenceQuality.STRONG
            authority, actionability, approval, status, conflicts = apply_policy(
                payload,
                deterministic_quality=deterministic_quality,
                deterministic_conflicts=snapshot.conflicts,
            )
            quality = min(
                (payload.evidence_quality, deterministic_quality),
                key={
                    EvidenceQuality.INSUFFICIENT: 0,
                    EvidenceQuality.CONFLICTING: 0,
                    EvidenceQuality.PARTIAL: 1,
                    EvidenceQuality.STRONG: 2,
                }.get,
            )
            decision = Decision(
                decision_id=str(uuid.uuid4()),
                status=status,
                confidence=payload.confidence,
                evidence_quality=quality,
                rationale=payload.rationale,
                evidence_references=payload.evidence_references,
                limitations=payload.limitations,
                conflicts=conflicts,
                missing_information=sorted(set(payload.missing_information + snapshot.missing_information)),
                recommended_action=payload.recommended_action,
                actionability=actionability,
                authority_mode=authority,
                approval_status=approval,
                provider=self.provider.name,
                provider_model=self.provider.model,
                snapshot_hash=snapshot.snapshot_hash,
            )
        # Provider implementations may raise arbitrary exceptions; all must fail closed.
        except Exception as exc:  # noqa: BLE001
            quality = (
                EvidenceQuality.INSUFFICIENT if snapshot.missing_information else EvidenceQuality.PARTIAL
            )
            decision = Decision(
                decision_id=str(uuid.uuid4()),
                status=DecisionStatus.NOT_ANALYZED,
                confidence=Confidence.LOW,
                evidence_quality=quality,
                rationale="Provider output was unavailable or failed validation; no recommendation was authorized.",
                evidence_references=[],
                limitations=["Provider analysis did not complete safely."],
                conflicts=snapshot.conflicts,
                missing_information=snapshot.missing_information,
                recommended_action="Obtain human analysis.",
                actionability=Actionability.NON_ACTIONABLE,
                authority_mode=AuthorityMode.HUMAN_ONLY,
                approval_status=ApprovalStatus.NOT_REQUIRED,
                provider=self.provider.name,
                provider_model=self.provider.model,
                snapshot_hash=snapshot.snapshot_hash,
            )
            provider_output = {"failure_type": type(exc).__name__}
        if self.repository:
            self.repository.save(decision, snapshot.model_dump(mode="json"), provider_output)
        return decision

    def decide_approval(self, decision_id: str, approve: bool, reviewer: str, note: str | None):
        current = self.repository.get(decision_id)
        if not current:
            return None
        if (
            current.authority_mode != AuthorityMode.APPROVAL_REQUIRED
            or current.approval_status != ApprovalStatus.PENDING
        ):
            raise ValueError("approval transition is not valid for this decision")
        status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        updated = current.model_copy(
            update={
                "approval_status": status,
                "actionability": Actionability.EXECUTABLE if approve else Actionability.NON_ACTIONABLE,
                "approval_reviewer": reviewer,
                "approval_note": note,
                "approval_at": datetime.now(UTC),
            }
        )
        self.repository.transition(decision_id, updated)
        return updated
