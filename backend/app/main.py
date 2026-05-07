import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import config

app = FastAPI(
    title="Fire Weather Predictor",
    description="API de detecção de hotspots e predição de risco de incêndio florestal",
    version="0.1.0",
)


@app.get("/health")
async def health() -> JSONResponse:
    """Verifica o status da API, banco de dados e Redis."""
    checks: dict = {"status": "ok", "db": "ok", "redis": "ok"}
    http_status = 200

    # Verifica conectividade com o PostgreSQL
    try:
        dsn = config.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn)
        await conn.fetchval("SELECT 1")
        await conn.close()
    except Exception as exc:
        checks["db"] = f"error: {exc}"
        checks["status"] = "degraded"
        http_status = 503

    # Verifica conectividade com o Redis
    try:
        r = aioredis.from_url(config.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        checks["status"] = "degraded"
        http_status = 503

    return JSONResponse(content=checks, status_code=http_status)
