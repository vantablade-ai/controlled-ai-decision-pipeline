"""Checks for the recording-focused demo against the real policy and audit store."""

from app.models import Actionability, ApprovalStatus, AuthorityMode, DecisionStatus, EvidenceQuality
from app.repositories.audit import AuditRepository
from scripts.linkedin_demo import build_results, present


def test_linkedin_demo_scenarios(tmp_path):
    repo = AuditRepository(str(tmp_path / "linkedin.sqlite3"))
    results = build_results(repo)
    assert results["conflicting"].confidence.value == "HIGH"
    assert results["conflicting"].evidence_quality == EvidenceQuality.CONFLICTING
    assert results["conflicting"].authority_mode == AuthorityMode.HUMAN_ONLY
    assert results["invalid"].status == DecisionStatus.NOT_ANALYZED
    assert results["invalid"].actionability == Actionability.NON_ACTIONABLE
    assert results["pending"].approval_status == ApprovalStatus.PENDING
    assert results["approved"].approval_status == ApprovalStatus.APPROVED
    assert repo.get(results["approved"].decision_id).approval_status == ApprovalStatus.APPROVED
    assert results["audit_records"] == 3


def test_linkedin_demo_presentation(tmp_path, monkeypatch, capsys):
    repo = AuditRepository(str(tmp_path / "linkedin.sqlite3"))
    results = build_results(repo)
    monkeypatch.setattr("builtins.input", lambda message: "")
    present(results, auto=False, delay=0, clear=False)
    output = capsys.readouterr().out
    assert "MOCK PROVIDER" in output
    assert "NO ACTION AUTHORIZED" in output
    assert "FAIL CLOSED" in output
    assert "APPROVAL RECORDED, NOT EXECUTED" in output
    assert "AI REASONING IS NOT AUTHORITY TO ACT" in output
