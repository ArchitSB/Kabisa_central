from types import SimpleNamespace

import pytest
import pytest_asyncio
from app.core.config import settings
from app.core.deps import get_current_user
from app.main import app
from app.models import AdminUser, DeliveryAgent, Role
from sqlalchemy import func, select


@pytest_asyncio.fixture
async def agent_staff(test_session_factory, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path))
    async with test_session_factory() as session:
        role = Role(name="agent_test_staff", description="Delivery-agent regression tests")
        session.add(role)
        await session.flush()
        user = AdminUser(
            name="Agent Tester",
            email="agent-tester@example.com",
            password_hash="unused",
            role_id=role.id,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        staff = SimpleNamespace(
            id=user.id,
            role=SimpleNamespace(
                permissions=[
                    SimpleNamespace(code=f"delivery_agents.{action}")
                    for action in ("view", "create", "edit")
                ]
            ),
        )
    app.dependency_overrides[get_current_user] = lambda: staff
    yield staff
    app.dependency_overrides.pop(get_current_user, None)


AGENT = {
    "name": "Test delivery rider",
    "phone": "0700000123",
    "email": "rider@example.com",
    "address": "Dar es Salaam",
    "vehicle_type": "MOTORCYCLE",
    "is_active": True,
}
PDF_PROOF = b"%PDF-1.4\nTest identity proof\n%%EOF"


@pytest.mark.parametrize("operation", ["create", "edit", "proof"])
async def test_agent_save_response_and_persistence(
    api_client, agent_staff, test_session_factory, operation
):
    created = await api_client.post("/api/v1/delivery-agents", json=AGENT)
    assert created.status_code == 201, created.text
    agent_id = created.json()["id"]
    url = f"/api/v1/delivery-agents/{agent_id}"
    response = created
    if operation == "edit":
        response = await api_client.patch(url, json={"name": "Updated delivery rider"})
        assert response.status_code == 200, response.text
        assert response.json()["name"] == "Updated delivery rider"
    elif operation == "proof":
        response = await api_client.post(
            f"{url}/id-proof", files={"file": ("identity.pdf", PDF_PROOF, "application/pdf")}
        )
        assert response.status_code == 200, response.text
        assert response.json()["id_proof_path"].endswith(".pdf")
        downloaded = await api_client.get(f"{url}/id-proof")
        assert downloaded.status_code == 200
        assert downloaded.content == PDF_PROOF
    assert response.json()["updated_at"]
    assert response.json()["created_by"] == str(agent_staff.id)
    # Read through another request/session, not an already populated identity map.
    detail = await api_client.get(url)
    assert detail.status_code == 200
    assert detail.json() == response.json()
    listed = await api_client.get("/api/v1/delivery-agents")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == agent_id
    async with test_session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(DeliveryAgent)) == 1


async def test_invalid_proof_can_be_retried_on_the_saved_agent(api_client, agent_staff):
    created = await api_client.post("/api/v1/delivery-agents", json=AGENT)
    assert created.status_code == 201
    url = f"/api/v1/delivery-agents/{created.json()['id']}/id-proof"
    rejected = await api_client.post(
        url, files={"file": ("identity.pdf", b"not a PDF", "application/pdf")}
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "invalid_proof_file"
    retry = await api_client.post(
        url, files={"file": ("identity.pdf", PDF_PROOF, "application/pdf")}
    )
    assert retry.status_code == 200, retry.text
    listed = await api_client.get("/api/v1/delivery-agents")
    assert listed.json()["total"] == 1
