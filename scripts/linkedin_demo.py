"""Recording-friendly demonstration of the real Controlled AI Decision Pipeline.

The evidence and provider responses are synthetic. This script calls the existing
ReasoningService, deterministic policy, approval transition, and SQLite audit store.
It does not contact an LLM, perform external actions, or simulate a production system.

Run from the repository root:
    python scripts/linkedin_demo.py
    python scripts/linkedin_demo.py --auto --delay 6
"""

import argparse
import sys
import tempfile
import time
from pathlib import Path

# Running `python scripts/linkedin_demo.py\` puts scripts/ on sys.path, not the repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.models import (  # noqa: E402
    Actionability,
    ApprovalStatus,
    AuthorityMode,
    DecisionStatus,
    EvidenceRequest,
    EvidenceQuality,
)
from app.providers.mock import MockProvider, MockScenario  # noqa: E402
from app.repositories.audit import AuditRepository  # noqa: E402
from app.services.reasoning import ReasoningService  # noqa: E402

WIDTH = 68


def load_example(filename: str) -> EvidenceRequest:
    return EvidenceRequest.model_validate_json((ROOT / "examples" / filename).read_text(encoding="utf-8"))


def build_results(repo: AuditRepository) -> dict:
    """Run genuine repository code and check that the presentation is truthful."""
    service = ReasoningService(MockProvider(), repo)

    # A mock provider expresses HIGH confidence, but deterministic validation
    # finds an incorrect failure_rate unit in the supplied synthetic evidence.
    conflicting = service.create(load_example("conflicting_evidence.json"))
    assert conflicting.confidence.value == "HIGH"
    assert conflicting.evidence_quality == EvidenceQuality.CONFLICTING
    assert conflicting.status == DecisionStatus.INVESTIGATE
    assert conflicting.authority_mode == AuthorityMode.HUMAN_ONLY
    assert conflicting.actionability == Actionability.NON_ACTIONABLE
    assert any("unit" in conflict for conflict in conflicting.conflicts)

    # The mock provider returns invalid schema data. The service fails closed.
    invalid = ReasoningService(MockProvider(MockScenario.INVALID_SCHEMA), repo).create(
        load_example("sufficient_evidence.json")
    )
    assert invalid.status == DecisionStatus.NOT_ANALYZED
    assert invalid.authority_mode == AuthorityMode.HUMAN_ONLY
    assert invalid.actionability == Actionability.NON_ACTIONABLE

    # A separate, valid synthetic recommendation still requires approval.
    pending = service.create(load_example("sufficient_evidence.json"))
    assert pending.authority_mode == AuthorityMode.APPROVAL_REQUIRED
    assert pending.approval_status == ApprovalStatus.PENDING
    assert pending.actionability == Actionability.PROPOSAL_ONLY
    assert repo.get(pending.decision_id) is not None

    # Synthetic reviewer transition. This does NOT execute an external action.
    approved = service.decide_approval(
        pending.decision_id, True, "reviewer-demo", "Demo-only approval transition"
    )
    assert approved is not None
    assert approved.approval_status == ApprovalStatus.APPROVED
    assert approved.actionability == Actionability.EXECUTABLE
    assert repo.get(approved.decision_id).approval_status == ApprovalStatus.APPROVED

    return {
        "conflicting": conflicting,
        "invalid": invalid,
        "pending": pending,
        "approved": approved,
        "conflicts": conflicting.conflicts,
        "audit_records": len(repo.list()),
    }


def show(title: str, lines: list[str], *, clear: bool) -> None:
    if clear:
        # Windows Terminal and VS Code's integrated terminal support ANSI clear.
        print("\033[2J\033[H", end="")
    print("=" * WIDTH)
    print("  VANTABLADE  /  CONTROLLED AI DECISION PIPELINE")
    print("  OFFLINE DEMO  |  MOCK PROVIDER  |  SYNTHETIC EVIDENCE")
    print("=" * WIDTH)
    print(f"\n  {title}\n")
    for line in lines:
        print(f"  {line}")
    print("\n" + "-" * WIDTH)
    print("  Demonstration only. No live AI or external action.", flush=True)


def advance(*, auto: bool, delay: float) -> None:
    if auto:
        time.sleep(delay)
    else:
        try:
            input("\n  Press Enter for the next scene... ")
        except EOFError:
            pass


def present(results: dict, *, auto: bool, delay: float, clear: bool) -> None:
    conflict = results["conflicting"]
    invalid = results["invalid"]
    pending = results["pending"]
    approved = results["approved"]
    scenes = [
        (
            "WHEN AI IS CONFIDENT ... BUT THE EVIDENCE IS WRONG",
            [
                "An AI recommendation should not decide its own authority.",
                "Watch three safeguards in a real Python decision pipeline.",
                "",
                "  1. Conflicting evidence",
                "  2. Invalid model output",
                "  3. Human approval",
            ],
        ),
        (
            "01  /  HIGH CONFIDENCE, CONFLICTING EVIDENCE",
            [
                f"Model confidence      {conflict.confidence.value}",
                f"Evidence quality      {conflict.evidence_quality.value}",
                f"Validation finding    {results['conflicts'][0]}",
                "",
                f"Policy decision       {conflict.status.value}",
                f"Authority             {conflict.authority_mode.value}",
                "RESULT                NO ACTION AUTHORIZED",
            ],
        ),
        (
            "02  /  INVALID MODEL OUTPUT",
            [
                "Simulated failure     Provider returned an invalid schema",
                "Validation            REJECTED",
                "",
                f"Policy decision       {invalid.status.value}",
                f"Authority             {invalid.authority_mode.value}",
                f"Actionability         {invalid.actionability.value}",
                "RESULT                FAIL CLOSED — NO ACTION",
            ],
        ),
        (
            "03  /  A VALID RECOMMENDATION STILL NEEDS APPROVAL",
            [
                "Suggested action      Create a review ticket",
                f"Evidence quality      {pending.evidence_quality.value}",
                "",
                f"Authority             {pending.authority_mode.value}",
                f"Approval              {pending.approval_status.value}",
                f"Actionability         {pending.actionability.value}",
                "RESULT                WAITING FOR A REVIEWER",
            ],
        ),
        (
            "04  /  APPROVAL TRANSITION RECORDED",
            [
                "Reviewer              reviewer-demo (synthetic)",
                f"Approval              PENDING -> {approved.approval_status.value}",
                f"Actionability         {approved.actionability.value}",
                f"SQLite audit records  {results['audit_records']}",
                "",
                "RESULT                APPROVAL RECORDED, NOT EXECUTED",
                "No customer system or external action was touched.",
            ],
        ),
        (
            "AI REASONING IS NOT AUTHORITY TO ACT.",
            [
                "Validate the evidence. Enforce the policy.",
                "Keep consequential decisions under human control.",
                "",
                "VANTABLADE  /  SOFTWARE ENGINEERING + APPLIED AI",
                "github.com/vantablade-ai/controlled-ai-decision-pipeline",
            ],
        ),
    ]
    for index, (title, lines) in enumerate(scenes):
        show(title, lines, clear=clear)
        if index < len(scenes) - 1:
            advance(auto=auto, delay=delay)
    if auto:
        time.sleep(delay)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a truthful, offline AI-control demonstration.")
    parser.add_argument("--auto", action="store_true", help="Advance scenes automatically (for Loom).")
    parser.add_argument("--delay", type=float, default=6.0, help="Seconds per scene in --auto mode.")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear the terminal between scenes.")
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay must be non-negative")
    with tempfile.TemporaryDirectory(prefix="vantablade-linkedin-demo-") as folder:
        repo = AuditRepository(str(Path(folder) / "demo.sqlite3"))
        results = build_results(repo)
        present(results, auto=args.auto, delay=args.delay, clear=not args.no_clear)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
