from app.models import EvidenceRequest, Observation

FAILURE_RATE_THRESHOLD = 0.10
MIN_SAMPLE_SIZE = 20


def derive_observations(request: EvidenceRequest) -> tuple[list[Observation], list[str]]:
    observations: list[Observation] = []
    conflicts: list[str] = []
    event_counts: dict[str, list] = {}
    for event in request.observed_events:
        event_counts.setdefault(event.kind.casefold(), []).append(event)
    for kind, events in sorted(event_counts.items()):
        if sum(event.count for event in events) >= 2:
            observations.append(
                Observation(
                    code="REPEATED_EVENT",
                    detail=f"Event kind '{kind}' occurred at least twice.",
                    evidence_references=[e.source_id for e in events],
                )
            )
    if request.manual_steps:
        observations.append(
            Observation(
                code="RECURRING_MANUAL_WORK",
                detail=f"{len(request.manual_steps)} manual step(s) were reported.",
            )
        )
    grouped_metrics: dict[str, list] = {}
    for metric in request.metrics:
        grouped_metrics.setdefault(metric.name.casefold(), []).append(metric)
    for name, values in sorted(grouped_metrics.items()):
        if len({(value.value, value.unit.casefold()) for value in values}) > 1:
            conflicts.append(f"metric '{name}' has conflicting recorded values or units")
    metrics = {metric.name.casefold(): metric for metric in request.metrics}
    sample = metrics.get("sample_size")
    failures = metrics.get("failure_rate")
    if sample and sample.value < MIN_SAMPLE_SIZE:
        observations.append(
            Observation(
                code="SMALL_SAMPLE",
                detail=f"Sample size {sample.value:g} is below {MIN_SAMPLE_SIZE}.",
                evidence_references=[sample.source_id],
            )
        )
    if failures and failures.value > FAILURE_RATE_THRESHOLD:
        observations.append(
            Observation(
                code="HIGH_FAILURE_RATE",
                detail=f"Failure rate {failures.value:g} exceeds {FAILURE_RATE_THRESHOLD:g}.",
                evidence_references=[failures.source_id],
            )
        )
    if failures and failures.unit.casefold() not in {"fraction", "ratio"}:
        conflicts.append("failure_rate unit must be fraction or ratio")
    if sample and sample.value < 0:
        conflicts.append("sample_size cannot be negative")
    if request.known_failures and not request.system_dependencies:
        observations.append(
            Observation(
                code="DEPENDENCY_UNVERIFIED", detail="Known failures are reported without dependency details."
            )
        )
    if request.missing_information:
        observations.append(
            Observation(
                code="REQUIRED_INFORMATION_MISSING",
                detail="The request lists information that is not available.",
            )
        )
    if not request.evidence_sources:
        observations.append(
            Observation(
                code="MISSING_EVIDENCE_SOURCE",
                detail="No source references were supplied for the evidence.",
            )
        )
    if (
        not request.observed_events
        and not request.metrics
        and not request.known_failures
        and not request.manual_steps
    ):
        observations.append(
            Observation(
                code="NO_MEASURED_EVIDENCE",
                detail="No events, metrics, failures, or manual steps were supplied.",
            )
        )
    return observations, conflicts
