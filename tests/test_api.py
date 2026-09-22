import httpx
import pytest


@pytest.mark.anyio
async def test_api_create_get_list_and_approval(client, evidence):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as api:
        response = await api.post("/decisions", json=evidence)
        assert response.status_code == 200
        decision = response.json()
        assert (await api.get("/decisions/" + decision["decision_id"])).status_code == 200
        assert len((await api.get("/decisions")).json()) == 1
        approved = await api.post(
            "/decisions/" + decision["decision_id"] + "/approve", json={"reviewer": "demo"}
        )
        assert approved.status_code == 200 and approved.json()["approval_status"] == "APPROVED"
        assert (
            await api.post("/decisions/" + decision["decision_id"] + "/reject", json={"reviewer": "demo"})
        ).status_code == 409


@pytest.mark.anyio
async def test_api_validation_and_missing(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as api:
        assert (
            await api.post("/decisions", content="not-json", headers={"content-type": "application/json"})
        ).status_code == 422
        assert (await api.get("/decisions/not-real")).status_code == 404
