from app.models import (
    Actionability,
    ApprovalStatus,
    AuthorityMode,
    DecisionStatus,
    EvidenceQuality,
    ProviderDecisionPayload,
)

SAFE_ACTIONS = {"CREATE_REVIEW_TICKET", "LOG_OBSERVATION", "QUEUE_FOLLOW_UP"}


def apply_policy(
    payload: ProviderDecisionPayload,
    *,
    deterministic_quality: EvidenceQuality,
    deterministic_conflicts: list[str],
) -> tuple[AuthorityMode, Actionability, ApprovalStatus, DecisionStatus, list[str]]:
    conflicts = sorted(set(payload.conflicts + deterministic_conflicts))
    quality_rank = {
        EvidenceQuality.INSUFFICIENT: 0,
        EvidenceQuality.CONFLICTING: 0,
        EvidenceQuality.PARTIAL: 1,
        EvidenceQuality.STRONG: 2,
    }
    quality = min((payload.evidence_quality, deterministic_quality), key=quality_rank.get)
    status = payload.status
    if (
        quality in {EvidenceQuality.INSUFFICIENT, EvidenceQuality.CONFLICTING}
        or conflicts
        or status == DecisionStatus.NOT_ANALYZED
    ):
        status = (
            DecisionStatus.NOT_ANALYZED
            if quality == EvidenceQuality.INSUFFICIENT or status == DecisionStatus.NOT_ANALYZED
            else DecisionStatus.INVESTIGATE
        )
        return (
            AuthorityMode.HUMAN_ONLY,
            Actionability.NON_ACTIONABLE,
            ApprovalStatus.NOT_REQUIRED,
            status,
            conflicts,
        )
    if status == DecisionStatus.NO_ACTION:
        return (
            AuthorityMode.HUMAN_ONLY,
            Actionability.NON_ACTIONABLE,
            ApprovalStatus.NOT_REQUIRED,
            status,
            conflicts,
        )
    authority = AuthorityMode.HUMAN_ONLY
    if payload.action_class in SAFE_ACTIONS and quality == EvidenceQuality.STRONG:
        authority = AuthorityMode.AUTO_SAFE
    elif quality == EvidenceQuality.PARTIAL or payload.status in {
        DecisionStatus.RECOMMEND,
        DecisionStatus.INVESTIGATE,
    }:
        authority = AuthorityMode.APPROVAL_REQUIRED
    if payload.requested_authority == AuthorityMode.HUMAN_ONLY or payload.action_class not in SAFE_ACTIONS:
        authority = AuthorityMode.HUMAN_ONLY
    elif (
        payload.requested_authority == AuthorityMode.APPROVAL_REQUIRED
        and authority == AuthorityMode.AUTO_SAFE
    ):
        authority = AuthorityMode.APPROVAL_REQUIRED
    approval = (
        ApprovalStatus.PENDING
        if authority == AuthorityMode.APPROVAL_REQUIRED
        else ApprovalStatus.NOT_REQUIRED
    )
    actionability = (
        Actionability.EXECUTABLE
        if authority == AuthorityMode.AUTO_SAFE
        else Actionability.PROPOSAL_ONLY
        if authority == AuthorityMode.APPROVAL_REQUIRED
        else Actionability.NON_ACTIONABLE
    )
    return authority, actionability, approval, status, conflicts
