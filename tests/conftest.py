import httpx
import pytest

from app.main import app
from app.providers.mock import MockProvider
from app.repositories.audit import AuditRepository
from app.services.reasoning import ReasoningService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def evidence():
    return {
        "subject": "Repeated manual reconciliation",
        "observed_events": [
            {"event_id": "e1", "kind": "reconciliation", "count": 3, "source_id": "log-1"},
            {"event_id": "e2", "kind": "reconciliation", "count": 2, "source_id": "log-2"},
        ],
        "metrics": [
            {"name": "sample_size", "value": 30, "unit": "records", "source_id": "metric-1"},
            {"name": "failure_rate", "value": 0.2, "unit": "fraction", "source_id": "metric-2"},
        ],
        "manual_steps": ["compare rows", "resolve mismatch"],
        "evidence_sources": ["system log", "weekly metrics"],
    }


@pytest.fixture
def repo(tmp_path):
    return AuditRepository(str(tmp_path / "audit.db"))


@pytest.fixture
def service(repo):
    return ReasoningService(MockProvider(), repo)


@pytest.fixture
def client(monkeypatch, tmp_path):
    from app import main

    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "api.db"))
    monkeypatch.setattr(main.settings, "provider", "mock")
    return httpx.ASGITransport(app=app)
