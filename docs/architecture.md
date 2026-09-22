# Architecture

## Evidence boundary

`EvidenceRequest` is typed and rejects unknown fields. It accepts events, metrics, reported failures, manual steps, dependencies, sources, and declared missing information. This demonstration assumes inputs are synthetic and supplied by a trusted caller; it does not authenticate evidence sources.

## Deterministic stage and snapshot

`derive_observations` checks repeated events, manual work, sample size, failure thresholds, missing information, and basic metric consistency. These observations are built before provider invocation and serialized into the snapshot. Canonical JSON uses sorted keys and compact separators; SHA-256 identifies the snapshot contents. The hash supports comparison and audit lookup, not authentication.

## Provider and validation

Providers return `ProviderDecisionPayload`; Pydantic rejects unknown fields and invalid enum values. The mock is deterministic and offline. The optional OpenAI adapter requests JSON Schema output, then runs the same local validation. Provider output can describe a proposal but has no field that can grant execution authority.

## Failure behavior

Exceptions, malformed objects, and schema failures produce an audited `NOT_ANALYZED` / `HUMAN_ONLY` result. Provider payload claims about quality are bounded by deterministic quality. Conflicts force investigation, while missing or absent evidence prevents actionability.

## Quality, confidence, and policy

Confidence expresses the provider's uncertainty; evidence quality is an independent deterministic ceiling combined with the provider's declared quality. The policy maps strong evidence and a small safe-action allowlist to `AUTO_SAFE`; partial evidence is at most `APPROVAL_REQUIRED`; insufficient or conflicting evidence is non-actionable and human-only. Any unlisted action is human-only. This is a narrow demonstration policy, not a general execution engine.

## Approval lifecycle and audit

Approval-required decisions begin `PENDING` and remain proposal-only. A single compare-and-update transition records approval or rejection with a synthetic reviewer label, note, and timestamp. SQLite stores the normalized snapshot, observations, validated provider output, final decision, authority, and approval status. API responses do not expose raw provider prompts or credentials.

## Limitations

The API has no authentication, source verification, rate limiting, or concurrent deployment strategy. Synthetic reviewer identity is not proof of identity. Model responses can be wrong even when valid. The repository demonstrates control boundaries and audit shape, not factual correctness or production-scale operation.
