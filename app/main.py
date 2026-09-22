import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import ApprovalRequest, Decision, EvidenceRequest, HealthResponse
from app.providers.mock import MockProvider
from app.providers.openai import OpenAIProvider
from app.repositories.audit import AuditRepository
from app.services.reasoning import ReasoningService

app = FastAPI(title="Controlled AI Decision Pipeline", version="1.0.0")


def build_service():
    if settings.provider == "openai":
        try:
            provider = OpenAIProvider()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None
    elif settings.provider == "mock":
        provider = MockProvider()
    else:
        raise HTTPException(status_code=503, detail="Configured provider is unavailable")
    try:
        repo = AuditRepository(settings.database_path)
    except (sqlite3.Error, OSError):
        raise HTTPException(status_code=503, detail="Audit persistence is unavailable") from None
    return ReasoningService(provider, repo)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Request validation failed"})


@app.post("/decisions", response_model=Decision)
async def create_decision(body: EvidenceRequest):
    service = build_service()
    try:
        return service.create(body)
    except (sqlite3.Error, OSError):
        raise HTTPException(status_code=503, detail="Decision could not be persisted") from None


@app.get("/decisions", response_model=list[Decision])
async def list_decisions():
    return build_service().repository.list()


@app.get("/decisions/{decision_id}", response_model=Decision)
async def get_decision(decision_id: str):
    decision = build_service().repository.get(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@app.post("/decisions/{decision_id}/approve", response_model=Decision)
async def approve(decision_id: str, body: ApprovalRequest):
    return await transition(decision_id, body, True)


@app.post("/decisions/{decision_id}/reject", response_model=Decision)
async def reject(decision_id: str, body: ApprovalRequest):
    return await transition(decision_id, body, False)


async def transition(decision_id: str, body: ApprovalRequest, approve: bool):
    service = build_service()
    try:
        decision = service.decide_approval(decision_id, approve, body.reviewer, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", provider=settings.provider)
