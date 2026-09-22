from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DecisionStatus(StrEnum):
    RECOMMEND = "RECOMMEND"
    INVESTIGATE = "INVESTIGATE"
    NO_ACTION = "NO_ACTION"
    NOT_ANALYZED = "NOT_ANALYZED"


class Confidence(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceQuality(StrEnum):
    INSUFFICIENT = "INSUFFICIENT"
    PARTIAL = "PARTIAL"
    STRONG = "STRONG"
    CONFLICTING = "CONFLICTING"


class AuthorityMode(StrEnum):
    AUTO_SAFE = "AUTO_SAFE"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    HUMAN_ONLY = "HUMAN_ONLY"


class ApprovalStatus(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Actionability(StrEnum):
    NON_ACTIONABLE = "NON_ACTIONABLE"
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    EXECUTABLE = "EXECUTABLE"


class Event(StrictModel):
    event_id: Text
    kind: Text
    count: int = Field(ge=0, le=1_000_000)
    source_id: Text


class Metric(StrictModel):
    name: Text
    value: float = Field(ge=0, le=1_000_000_000)
    unit: Text
    source_id: Text


class EvidenceRequest(StrictModel):
    subject: Text
    observed_events: list[Event] = Field(default_factory=list, max_length=100)
    metrics: list[Metric] = Field(default_factory=list, max_length=100)
    known_failures: list[Text] = Field(default_factory=list, max_length=50)
    manual_steps: list[Text] = Field(default_factory=list, max_length=50)
    system_dependencies: list[Text] = Field(default_factory=list, max_length=50)
    evidence_sources: list[Text] = Field(default_factory=list, max_length=100)
    missing_information: list[Text] = Field(default_factory=list, max_length=50)


class Observation(StrictModel):
    code: Text
    detail: Text
    evidence_references: list[Text] = Field(default_factory=list)


class EvidenceSnapshot(StrictModel):
    schema_version: str = "1.0.0"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request: EvidenceRequest
    observations: list[Observation]
    conflicts: list[str]
    missing_information: list[str]
    snapshot_hash: str


class ProviderDecisionPayload(StrictModel):
    status: DecisionStatus
    confidence: Confidence
    evidence_quality: EvidenceQuality
    rationale: Text
    evidence_references: list[Text] = Field(default_factory=list)
    limitations: list[Text] = Field(default_factory=list)
    conflicts: list[Text] = Field(default_factory=list)
    missing_information: list[Text] = Field(default_factory=list)
    recommended_action: Text
    action_class: Text
    requested_authority: AuthorityMode


class Decision(StrictModel):
    decision_id: str
    status: DecisionStatus
    confidence: Confidence
    evidence_quality: EvidenceQuality
    rationale: str
    evidence_references: list[str]
    limitations: list[str]
    conflicts: list[str]
    missing_information: list[str]
    recommended_action: str
    actionability: Actionability
    authority_mode: AuthorityMode
    approval_status: ApprovalStatus
    provider: str
    provider_model: str | None = None
    snapshot_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    approval_reviewer: str | None = None
    approval_note: str | None = None
    approval_at: datetime | None = None


class ApprovalRequest(StrictModel):
    reviewer: Text
    note: str | None = Field(default=None, max_length=500)


class HealthResponse(StrictModel):
    status: str
    provider: str
    version: str = "1.0.0"
