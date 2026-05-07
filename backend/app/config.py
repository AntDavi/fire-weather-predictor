import os

# Configurações carregadas via variáveis de ambiente.
# Na Issue #1.5 será migrado para pydantic-settings.

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://fireweather:fireweather@localhost:5432/fireweather",
)
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
APP_ENV: str = os.environ.get("APP_ENV", "development")
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

CACHE_TTL_RISK: int = int(os.environ.get("CACHE_TTL_RISK", "3600"))
CACHE_TTL_WEATHER: int = int(os.environ.get("CACHE_TTL_WEATHER", "1800"))
CACHE_TTL_HOTSPOTS: int = int(os.environ.get("CACHE_TTL_HOTSPOTS", "900"))
