def test_audit_persists_provenance(service, evidence, repo):
    from app.models import EvidenceRequest

    decision = service.create(EvidenceRequest.model_validate(evidence))
    assert repo.get(decision.decision_id) == decision
    assert decision.snapshot_hash


def test_approval_lifecycle(service, evidence):
    from app.models import ApprovalStatus, EvidenceRequest

    decision = service.create(EvidenceRequest.model_validate(evidence))
    assert decision.approval_status == ApprovalStatus.PENDING
    approved = service.decide_approval(decision.decision_id, True, "reviewer-demo", "Reviewed")
    assert approved.approval_status == ApprovalStatus.APPROVED
    try:
        service.decide_approval(decision.decision_id, False, "reviewer-demo", None)
    except ValueError:
        pass
    else:
        raise AssertionError("conflicting approval transition accepted")
