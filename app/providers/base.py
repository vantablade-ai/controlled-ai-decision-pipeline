from typing import Protocol

from app.models import EvidenceSnapshot, ProviderDecisionPayload


class ReasoningProvider(Protocol):
    name: str
    model: str | None

    def analyze(self, snapshot: EvidenceSnapshot) -> ProviderDecisionPayload: ...
