import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.models import EvidenceRequest
from app.providers.mock import MockProvider, MockScenario
from app.repositories.audit import AuditRepository
from app.services.reasoning import ReasoningService


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="controlled-ai-demo-") as folder:
        repo = AuditRepository(str(Path(folder) / "demo.sqlite3"))
        service = ReasoningService(MockProvider(), repo)
        print("Controlled AI Decision Pipeline — demo\n")
        strong = EvidenceRequest.model_validate_json((root / "examples/sufficient_evidence.json").read_text())
        first = service.create(strong)
        print(
            f"[{first.status}] {strong.subject}\nEvidence: {first.evidence_quality} | Authority: {first.authority_mode} | Snapshot: {first.snapshot_hash[:12]}"
        )
        assert first.actionability.value == "PROPOSAL_ONLY"
        approved = service.decide_approval(
            first.decision_id, True, "reviewer-demo", "Synthetic review complete"
        )
        assert approved.approval_status.value == "APPROVED"
        print("[APPROVAL] pending → approved")
        partial_request = EvidenceRequest(
            subject="Manual exception review",
            manual_steps=["inspect exception queue"],
            evidence_sources=["operator log"],
        )
        partial_decision = service.create(partial_request)
        assert partial_decision.authority_mode.value == "APPROVAL_REQUIRED"
        print(f"[{partial_decision.status}] partial evidence | Authority: {partial_decision.authority_mode}")
        partial = EvidenceRequest.model_validate_json(
            (root / "examples/insufficient_evidence.json").read_text()
        )
        second = service.create(partial)
        assert second.status.value == "NOT_ANALYZED" and second.actionability.value == "NON_ACTIONABLE"
        print(f"[{second.status}] insufficient evidence | Authority: {second.authority_mode}")
        conflict = EvidenceRequest.model_validate_json(
            (root / "examples/conflicting_evidence.json").read_text()
        )
        third = service.create(conflict)
        assert third.status.value == "INVESTIGATE" and third.conflicts
        print(f"[{third.status}] conflicting evidence | {len(third.conflicts)} conflict(s) recorded")
        invalid = ReasoningService(MockProvider(MockScenario.INVALID_SCHEMA), repo).create(strong)
        assert invalid.status.value == "NOT_ANALYZED" and invalid.authority_mode.value == "HUMAN_ONLY"
        print("[SAFE FAILURE] invalid provider output bounded")
        failed = ReasoningService(MockProvider(MockScenario.ERROR), repo).create(strong)
        assert failed.status.value == "NOT_ANALYZED" and failed.actionability.value == "NON_ACTIONABLE"
        print("[SAFE FAILURE] provider exception bounded")
        stored = repo.get(first.decision_id)
        assert stored.snapshot_hash == first.snapshot_hash and stored.approval_status.value == "APPROVED"
        print(f"[AUDIT] {stored.decision_id[:8]} snapshot/provenance retained")
        print("\nAll control invariants passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
