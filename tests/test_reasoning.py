import pytest

from app.models import ApprovalStatus, AuthorityMode, DecisionStatus
from app.providers.mock import MockProvider, MockScenario
from app.services.reasoning import ReasoningService


@pytest.mark.parametrize("scenario", [MockScenario.ERROR, MockScenario.INVALID_SCHEMA])
def test_provider_failure_is_bounded_and_audited(evidence, repo, scenario):
    decision = ReasoningService(MockProvider(scenario), repo).create(
        __import__("app.models", fromlist=["EvidenceRequest"]).EvidenceRequest.model_validate(evidence)
    )
    assert decision.status == DecisionStatus.NOT_ANALYZED
    assert decision.authority_mode == AuthorityMode.HUMAN_ONLY
    assert repo.get(decision.decision_id) == decision


def test_valid_and_low_confidence_outputs(evidence, repo):
    from app.models import EvidenceRequest

    d = ReasoningService(MockProvider(), repo).create(EvidenceRequest.model_validate(evidence))
    assert d.snapshot_hash and d.approval_status == ApprovalStatus.PENDING
    d2 = ReasoningService(MockProvider(MockScenario.LOW_CONFIDENCE), repo).create(
        EvidenceRequest.model_validate(evidence)
    )
    assert d2.confidence.value == "LOW"


def test_insufficient_request_not_actionable(repo):
    from app.models import EvidenceRequest

    decision = ReasoningService(MockProvider(), repo).create(
        EvidenceRequest(subject="unknown", evidence_sources=["intake"], missing_information=["metrics"])
    )
    assert decision.status == DecisionStatus.NOT_ANALYZED
    assert decision.actionability.value == "NON_ACTIONABLE"


def test_provider_cannot_change_observation_list(evidence, repo):
    from app.models import EvidenceRequest

    decision = ReasoningService(MockProvider(), repo).create(EvidenceRequest.model_validate(evidence))
    stored = repo.get_snapshot(decision.decision_id)
    assert stored["snapshot_hash"] == decision.snapshot_hash
    assert {item["code"] for item in stored["observations"]} >= {
        "REPEATED_EVENT",
        "HIGH_FAILURE_RATE",
        "RECURRING_MANUAL_WORK",
    }


def test_conflicts_and_not_analyzed_scenarios_are_bounded(evidence, repo):
    from app.models import EvidenceRequest
    from app.providers.mock import MockScenario

    request = EvidenceRequest.model_validate(evidence)
    conflicting = ReasoningService(MockProvider(MockScenario.CONFLICTING), repo).create(request)
    assert conflicting.authority_mode == AuthorityMode.HUMAN_ONLY
    not_analyzed = ReasoningService(MockProvider(MockScenario.NOT_ANALYZED), repo).create(request)
    assert not_analyzed.actionability.value == "NON_ACTIONABLE"


def test_provider_cannot_reference_absent_source(evidence, repo):
    from app.models import EvidenceRequest, ProviderDecisionPayload

    class FalseReferenceProvider:
        name = "test"
        model = None

        def analyze(self, snapshot):
            payload = MockProvider().analyze(snapshot).model_dump()
            payload["evidence_references"] = ["invented-source"]
            return ProviderDecisionPayload.model_validate(payload)

    decision = ReasoningService(FalseReferenceProvider(), repo).create(
        EvidenceRequest.model_validate(evidence)
    )
    assert decision.status == DecisionStatus.NOT_ANALYZED
    assert decision.authority_mode == AuthorityMode.HUMAN_ONLY
