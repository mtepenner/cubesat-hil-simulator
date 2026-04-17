"""Integration tests for the FastAPI simulation API."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "CubeSat" in response.json()["service"]


@pytest.mark.anyio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_get_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sim/status")
    assert response.status_code == 200
    data = response.json()
    assert "orbit" in data
    assert "environment" in data
    assert "dynamics" in data


@pytest.mark.anyio
async def test_step_simulation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sim/step", json={"steps": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["sim_time"] > 0


@pytest.mark.anyio
async def test_start_pause_stop():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/sim/start")
        assert r.status_code == 200
        assert r.json()["status"] == "running"

        r = await client.post("/api/sim/pause")
        assert r.status_code == 200
        assert r.json()["status"] == "paused"

        r = await client.post("/api/sim/stop")
        assert r.status_code == 200
        assert r.json()["status"] == "stopped"


@pytest.mark.anyio
async def test_configure_simulation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sim/config", json={"dt": 0.5, "time_scale": 2.0})
    assert response.status_code == 200
    data = response.json()
    assert data["dt"] == 0.5
    assert data["time_scale"] == 2.0
