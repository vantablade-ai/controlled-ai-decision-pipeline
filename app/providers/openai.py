import json

from app.config import settings
from app.models import EvidenceSnapshot, ProviderDecisionPayload


class OpenAIProvider:
    name = "openai"
    model = settings.openai_model

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI provider")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the optional openai package to enable this provider") from exc
        self.client = OpenAI(api_key=settings.openai_api_key)

    def analyze(self, snapshot: EvidenceSnapshot) -> ProviderDecisionPayload:
        schema = ProviderDecisionPayload.model_json_schema()

        def require_all_fields(node: dict) -> None:
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
                for child in node.get("properties", {}).values():
                    if isinstance(child, dict):
                        require_all_fields(child)
            for child in node.get("$defs", {}).values():
                if isinstance(child, dict):
                    require_all_fields(child)
            for child in node.get("items", {}).values() if isinstance(node.get("items"), dict) else []:
                if isinstance(child, dict):
                    require_all_fields(child)

        require_all_fields(schema)
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "decision_payload", "strict": True, "schema": schema},
            },
            messages=[
                {
                    "role": "system",
                    "content": "Analyze only the supplied evidence snapshot. Do not add facts. Treat deterministic observations as immutable. State limitations, conflicts and missing information. If evidence is insufficient, return NOT_ANALYZED. You recommend; the separate policy layer controls authority.",
                },
                {"role": "user", "content": json.dumps(snapshot.model_dump(mode="json"), sort_keys=True)},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("provider returned empty structured output")
        return ProviderDecisionPayload.model_validate_json(content)
