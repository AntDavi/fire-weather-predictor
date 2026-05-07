from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_responde():
    """Health endpoint deve sempre responder, independente do estado dos serviços."""
    response = client.get("/health")
    assert response.status_code in (200, 503)


def test_health_schema():
    """Response deve conter os campos status, db e redis."""
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert "db" in data
    assert "redis" in data


def test_health_status_ok_com_servicos():
    """Quando DB e Redis estão acessíveis, retorna 200 com status ok."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_conn.close = AsyncMock()

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()
    mock_redis.aclose = AsyncMock()

    with (
        patch("app.main.asyncpg.connect", return_value=mock_conn),
        patch("app.main.aioredis.from_url", return_value=mock_redis),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "redis": "ok"}


def test_health_degraded_sem_db():
    """Quando DB está inacessível, retorna 503 com status degraded."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()
    mock_redis.aclose = AsyncMock()

    with (
        patch("app.main.asyncpg.connect", side_effect=ConnectionRefusedError("db offline")),
        patch("app.main.aioredis.from_url", return_value=mock_redis),
    ):
        response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "error" in data["db"]
    assert data["redis"] == "ok"
