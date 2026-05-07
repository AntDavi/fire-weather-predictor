# CLAUDE.md — Fire Weather Predictor
> Especificação Viva. Leia este arquivo inteiro antes de qualquer ação.
> Última atualização: início do projeto.

---

## 1. Visão Geral do Projeto

**Nome**: Fire Weather Predictor  
**Descrição**: API REST que detecta hotspots de queimadas e prediz risco de incêndio florestal em tempo real, com geração de alertas para mitigação ambiental.  
**Contexto acadêmico**: 32º Prêmio Jovem Cientista CNPq 2026 — Tema "IA & Meio Ambiente"  
**Região de foco**: Ceará, Brasil (expansível para todo o Nordeste)  
**Stack principal**: FastAPI + PostgreSQL/PostGIS + XGBoost + SHAP + Leaflet.js  

### Objetivo do Sistema
- Receber: `latitude`, `longitude`, `radius_km`
- Retornar: GeoJSON com células de risco (0–100%), nível (`low/medium/high`), explicação via SHAP

---

## 2. Arquitetura

```
┌── INMET API           → temperatura, umidade, vento, chuva (horário)
├── NASA FIRMS API      → hotspots de calor (3x/dia, bbox endpoint)
├── BDQueimadas INPE    → queimadas consolidadas (1x/dia, fallback)
├── Sentinel-2          → NDVI (a cada 5 dias)
└── INPE Histórico      → queimadas 2003–2024 (backfill inicial)
        │
        ▼
   PostgreSQL + PostGIS (6 tabelas, índices geoespaciais)
        │
        ▼
   Feature Engineering (FWI, NDVI delta, hotspot density, histórico)
        │
        ▼
   XGBoost Model (risco 0–100%) + SHAP (explicabilidade)
        │
        ▼
   FastAPI (4 endpoints REST)
        │
        ▼
   Frontend Leaflet.js (mapa + pins coloridos por risco)
```

### Hybrid Data Approach (CRÍTICO)
- FIRMS endpoint `country` está indisponível desde Maio 2026
- **Solução**: usar endpoint de área (`bbox`) do FIRMS
- **Fallback**: BDQueimadas INPE se FIRMS falhar
- **Degraded mode**: se ambas falharem, usar dados históricos com warning

---

## 3. Stack Tecnológico

| Camada | Tecnologia | Versão | Justificativa |
|--------|-----------|--------|--------------|
| Backend | FastAPI | ≥0.110 | Assíncrono, OpenAPI automático |
| Banco | PostgreSQL | 15 | Geoespacial nativo com PostGIS |
| Extensão geo | PostGIS | 3.4 | Queries ST_Within, ST_Distance |
| Cache | Redis | 7 | TTL configurável por tipo de dado |
| ML | XGBoost | ≥2.0 | Interpretável, rápido, produção-ready |
| Explicabilidade | SHAP | ≥0.45 | TreeExplainer para XGBoost |
| Frontend | Leaflet.js | 1.9 | Mapa leve, sem framework pesado |
| Deploy | Docker + Docker Compose | - | Portabilidade total |
| CI/CD | GitHub Actions | - | Automatizado no push |
| Infra prod | Railway ou Fly.io | - | Free tier suficiente para MVP |

### Dependências Python (requirements.txt)
```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0
asyncpg>=0.29
geoalchemy2>=0.14
redis>=5.0
xgboost>=2.0
shap>=0.45
pandas>=2.0
numpy>=1.26
httpx>=0.27
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=4.1
ruff
bandit
```

---

## 4. Schema do Banco de Dados

```sql
-- Extensões obrigatórias
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb; -- opcional, para séries temporais

-- 1. Estações meteorológicas
CREATE TABLE weather_stations (
    id SERIAL PRIMARY KEY,
    station_code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100),
    location GEOMETRY(Point, 4326) NOT NULL,
    state VARCHAR(2),
    active BOOLEAN DEFAULT TRUE
);

-- 2. Leituras meteorológicas (série temporal)
CREATE TABLE weather_readings (
    id BIGSERIAL PRIMARY KEY,
    station_id INTEGER REFERENCES weather_stations(id),
    recorded_at TIMESTAMPTZ NOT NULL,
    temperature_c FLOAT,
    humidity_pct FLOAT,
    wind_speed_ms FLOAT,
    wind_direction_deg FLOAT,
    precipitation_mm FLOAT,
    UNIQUE(station_id, recorded_at)
);
CREATE INDEX idx_weather_readings_station_time 
    ON weather_readings(station_id, recorded_at DESC);

-- 3. Hotspots (FIRMS + INPE)
CREATE TABLE hotspots (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL, -- 'FIRMS_VIIRS', 'FIRMS_MODIS', 'INPE'
    detected_at TIMESTAMPTZ NOT NULL,
    location GEOMETRY(Point, 4326) NOT NULL,
    brightness_k FLOAT,        -- temperatura de brilho
    frp_mw FLOAT,              -- Fire Radiative Power
    confidence VARCHAR(10),    -- 'low', 'nominal', 'high'
    raw_data JSONB
);
CREATE INDEX idx_hotspots_location ON hotspots USING GIST(location);
CREATE INDEX idx_hotspots_detected_at ON hotspots(detected_at DESC);

-- 4. Índices de vegetação (NDVI via Sentinel-2)
CREATE TABLE ndvi_readings (
    id BIGSERIAL PRIMARY KEY,
    location GEOMETRY(Point, 4326) NOT NULL,
    measured_at DATE NOT NULL,
    ndvi_value FLOAT CHECK (ndvi_value BETWEEN -1.0 AND 1.0),
    cloud_coverage_pct FLOAT,
    UNIQUE(location, measured_at)
);
CREATE INDEX idx_ndvi_location ON ndvi_readings USING GIST(location);

-- 5. Predições de risco
CREATE TABLE risk_predictions (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    cell_location GEOMETRY(Point, 4326) NOT NULL,
    radius_km FLOAT NOT NULL,
    risk_probability FLOAT CHECK (risk_probability BETWEEN 0 AND 100),
    risk_level VARCHAR(10) CHECK (risk_level IN ('low', 'medium', 'high')),
    fwi_score FLOAT,           -- Fire Weather Index
    ndvi_score FLOAT,
    hotspot_density FLOAT,
    historical_risk FLOAT,
    shap_values JSONB,         -- explicabilidade por feature
    model_version VARCHAR(20)
);
CREATE INDEX idx_predictions_location ON risk_predictions USING GIST(cell_location);
CREATE INDEX idx_predictions_created_at ON risk_predictions(created_at DESC);

-- 6. Histórico de queimadas (INPE 2003–2024)
CREATE TABLE fire_history (
    id BIGSERIAL PRIMARY KEY,
    occurred_at DATE NOT NULL,
    location GEOMETRY(Point, 4326) NOT NULL,
    municipality VARCHAR(100),
    state VARCHAR(2),
    area_ha FLOAT,
    source VARCHAR(20) DEFAULT 'INPE'
);
CREATE INDEX idx_fire_history_location ON fire_history USING GIST(location);
CREATE INDEX idx_fire_history_date ON fire_history(occurred_at DESC);
```

---

## 5. Endpoints da API

```
GET  /health
     → Status da API, DB, Redis, dados mais recentes

GET  /api/v1/risk
     Query: lat, lon, radius_km (default=20)
     → GeoJSON com cells de risco

GET  /api/v1/hotspots
     Query: lat, lon, radius_km, hours_back (default=24)
     → Lista de hotspots recentes na área

GET  /api/v1/weather
     Query: lat, lon
     → Dados meteorológicos da estação mais próxima

POST /api/v1/risk/batch
     Body: [{lat, lon, radius_km}]
     → Múltiplas predições (máx 10 por request)
```

### Response: /api/v1/risk
```json
{
  "type": "FeatureCollection",
  "generated_at": "2026-05-01T10:30:00Z",
  "query": {"lat": -3.73, "lon": -38.52, "radius_km": 20},
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [-38.52, -3.73]},
      "properties": {
        "risk_probability": 72.4,
        "risk_level": "high",
        "fwi_score": 45.2,
        "ndvi": 0.23,
        "hotspot_count_24h": 3,
        "historical_risk_percentile": 89,
        "explanation": {
          "top_factors": ["fwi_score", "hotspot_density", "low_ndvi"],
          "shap_values": {"fwi_score": 0.31, "hotspot_density": 0.28, "ndvi": -0.19}
        },
        "data_freshness": {
          "weather": "2026-05-01T09:00:00Z",
          "hotspots": "2026-05-01T10:00:00Z",
          "ndvi": "2026-04-28T00:00:00Z"
        }
      }
    }
  ]
}
```

---

## 6. Feature Engineering

### Fire Weather Index (FWI)
O FWI canadense é composto por:
- **FFMC** (Fine Fuel Moisture Code): umidade de combustível fino — usa temperatura, umidade, vento, chuva
- **DMC** (Duff Moisture Code): umidade de camada orgânica moderada
- **DC** (Drought Code): seca profunda
- **ISI** (Initial Spread Index): velocidade inicial de propagação
- **BUI** (Buildup Index): combustível disponível total
- **FWI** (Fire Weather Index): índice final (0–100+)

### Features do Modelo XGBoost
```python
FEATURES = [
    # Meteorológicas
    'temperature_c',        # temperatura atual
    'humidity_pct',         # umidade relativa
    'wind_speed_ms',        # velocidade do vento
    'precipitation_7d_mm',  # chuva acumulada 7 dias
    
    # FWI
    'fwi_score',            # índice FWI calculado
    'ffmc_score',
    'dmc_score',
    'dc_score',
    
    # Vegetação
    'ndvi_current',         # NDVI mais recente
    'ndvi_delta_30d',       # variação NDVI em 30 dias
    
    # Hotspots
    'hotspot_count_24h',    # hotspots nas últimas 24h, raio 50km
    'hotspot_count_7d',     # hotspots nos últimos 7 dias, raio 50km
    'nearest_hotspot_km',   # distância ao hotspot mais próximo
    
    # Histórico
    'historical_fire_count_5y',     # queimadas nos últimos 5 anos (mesma célula)
    'historical_fire_month_avg',    # média histórica para o mês atual
    
    # Temporal
    'month',                # mês (sazonalidade)
    'day_of_year',          # dia do ano
]
```

---

## 7. Estrutura de Diretórios

```
fire-weather-predictor/
├── CLAUDE.md                    ← você está aqui
├── TODO.md                      ← roadmap de issues
├── README.md
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                 ← migrations
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py              ← FastAPI app
│   │   ├── config.py            ← settings via pydantic-settings
│   │   ├── database.py          ← async SQLAlchemy engine
│   │   ├── models/              ← SQLAlchemy models
│   │   │   ├── weather.py
│   │   │   ├── hotspot.py
│   │   │   ├── ndvi.py
│   │   │   └── prediction.py
│   │   ├── schemas/             ← Pydantic schemas
│   │   ├── routers/             ← endpoints
│   │   │   ├── risk.py
│   │   │   ├── hotspots.py
│   │   │   └── weather.py
│   │   ├── services/            ← lógica de negócio
│   │   │   ├── risk_predictor.py
│   │   │   ├── feature_engineer.py
│   │   │   └── cache_service.py
│   │   ├── collectors/          ← coleta de dados externos
│   │   │   ├── inmet_collector.py
│   │   │   ├── firms_collector.py
│   │   │   ├── bdqueimadas_collector.py
│   │   │   └── sentinel_collector.py
│   │   └── ml/
│   │       ├── model.py         ← wrapper XGBoost
│   │       ├── fwi_calculator.py
│   │       └── train.py
│   └── tests/
│       ├── conftest.py
│       ├── test_collectors/
│       ├── test_services/
│       ├── test_routers/
│       └── test_ml/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js                   ← Leaflet.js map
├── scripts/
│   ├── backfill_history.py      ← INPE 2003-2024
│   ├── train_model.py
│   └── ci.sh                    ← script CI local
└── notebooks/
    ├── eda.ipynb                 ← exploração inicial
    └── model_evaluation.ipynb
```

---

## 8. Convencões de Código

- **Linguagem do código**: inglês (nomes de funções, variáveis, classes)
- **Comentários/docs**: português (este é um projeto acadêmico brasileiro)
- **Estilo Python**: `ruff` como linter/formatter, configuração padrão
- **Type hints**: obrigatórios em todas as funções públicas
- **Async**: todos os endpoints e queries ao banco devem ser `async`
- **Commits**: `tipo: descrição curta` — ex: `feat: endpoint /risk`, `fix: FIRMS bbox fallback`
- **Branches**: `feature/nome`, `fix/nome`, `chore/nome`
- **Testes**: arquivo `test_<módulo>.py` espelhando a estrutura em `app/`

### Padrão de Commit
```
feat: nova funcionalidade
fix: correção de bug
test: adiciona/modifica testes
refactor: refatoração sem mudança de comportamento
chore: CI, Docker, dependências
docs: atualização de documentação
```

---

## 9. Restrições (NAO Viole Sem Aprovação Explícita)

- **NAO** adicione dependências Python sem aprovação — cada nova lib vai no requirements.txt e justificada
- **NAO** faça queries sem usar índices geoespaciais (ST_DWithin com `&&` antes de ST_Within)
- **NAO** exponga secrets em código — sempre via variáveis de ambiente (.env)
- **NAO** faça requests síncronos em endpoints FastAPI — sempre `httpx.AsyncClient`
- **NAO** persista dados brutos de API sem validação Pydantic
- **NAO** commite sem rodar `scripts/ci.sh` primeiro
- **NAO** faça cache de predições por mais de 1 hora (dados de hotspot mudam frequentemente)
- **NAO** use `float` para coordenadas geográficas no banco — use `GEOMETRY(Point, 4326)`

---

## 10. Fluxo de Trabalho (Obrigatório)

```
1. Leia este CLAUDE.md completo
2. Para cada issue: explique o plano ANTES de codificar
3. Aguarde aprovação do plano
4. Implemente com testes
5. Rode scripts/ci.sh
6. Só então declare concluído
```

### Checklist Antes de Declarar Issue Concluída
- [ ] Testes unitários escritos e passando
- [ ] `ruff check .` sem erros
- [ ] `bandit -r app/` sem issues críticas
- [ ] `pytest --cov=app tests/` cobertura ≥ 70%
- [ ] `scripts/ci.sh` verde
- [ ] CLAUDE.md atualizado se houver nova decisão de design

---

## 11. Variáveis de Ambiente (.env.example)

```bash
# Banco
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fireweather
REDIS_URL=redis://localhost:6379/0

# APIs externas (gratuitas)
FIRMS_MAP_KEY=your_firms_api_key_here         # firms.modaps.eosdis.nasa.gov
INMET_TOKEN=your_inmet_token_here             # apitempo.inmet.gov.br
SENTINEL_HUB_CLIENT_ID=your_client_id        # sentinel-hub.com
SENTINEL_HUB_CLIENT_SECRET=your_secret

# App
APP_ENV=development                           # development | production
LOG_LEVEL=INFO
CACHE_TTL_RISK=3600                           # 1 hora
CACHE_TTL_WEATHER=1800                        # 30 min
CACHE_TTL_HOTSPOTS=900                        # 15 min

# ML
MODEL_VERSION=v1
MIN_HOTSPOT_CONFIDENCE=nominal                # low | nominal | high
```

---

## 12. Hurdles Conhecidos

| Problema | Status | Solução |
|----------|--------|---------|
| FIRMS `country` endpoint indisponível (Mai/2026) | RESOLVIDO | Usar `bbox` endpoint + BDQueimadas fallback |
| INMET API sem dados históricos > 1 ano | CONHECIDO | Para histórico usar CSV BDMEP do INMET |
| Sentinel-2 com cobertura de nuvem no CE | CONHECIDO | Usar última leitura válida (máx 5 dias) |
| NDVI interpolação entre leituras (5 dias) | PENDENTE | Linear interpolation entre readings |
| BDQueimadas INPE usa paginação não-documentada | PENDENTE | Investigar ao implementar |
| XGBoost precisa de dados balanceados (poucos "high risk") | PENDENTE | SMOTE ou class_weight no training |

---

## 13. Decisões de Design

| Decisão | Escolha | Alternativa Rejeitada | Motivo |
|---------|---------|----------------------|--------|
| ML model | XGBoost | Random Forest, LSTM | Interpretável via SHAP, rápido, aceito em papers |
| Banco geoespacial | PostGIS | MongoDB, ElasticSearch | Queries ST_Within nativas, SQL padrão |
| API format | GeoJSON | JSON customizado | Padrão geoespacial, Leaflet consome direto |
| Frontend | Leaflet.js | React + Mapbox | Simples, leve, sem API key paga |
| Cache granularidade | Por endpoint | Por célula geográfica | Mais simples para MVP |
| FWI | Implementação manual | Biblioteca externa | Controle total, sem dependência |

---

## 14. Cache Strategy

```
/api/v1/risk?lat=X&lon=Y&radius=Z
  → cache key: f"risk:{round(lat,3)}:{round(lon,3)}:{radius_km}"
  → TTL: 3600s (1 hora)

/api/v1/hotspots?...
  → cache key: f"hotspots:{round(lat,2)}:{round(lon,2)}:{hours_back}"
  → TTL: 900s (15 min)

/api/v1/weather?...
  → cache key: f"weather:{round(lat,2)}:{round(lon,2)}"
  → TTL: 1800s (30 min)
```

---

## 15. Script CI Local (scripts/ci.sh)

```bash
#!/bin/bash
set -e

echo "==> Ruff (linter)..."
ruff check .

echo "==> Bandit (security scan)..."
bandit -r app/ -ll

echo "==> Pytest (tests + coverage)..."
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=70

echo ""
echo "✅ CI PASSED!"
```

---

## 16. Roadmap de Fontes de Dados

### FIRMS (NASA) — Hotspots
- **URL**: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/{bbox}/{days}`
- **Bbox Ceará**: `-41.5,-7.9,-37.2,-2.7`
- **Frequência**: 3x/dia (near-real-time)
- **Campos úteis**: latitude, longitude, bright_ti4, frp, confidence, acq_date, acq_time

### INMET — Dados Meteorológicos
- **URL**: `https://apitempo.inmet.gov.br/token/{TOKEN}/estacao/{DATA_INI}/{DATA_FIM}/{CODIGO}`
- **Estações no CE**: ~30 estações automáticas
- **Frequência**: horária
- **Campos úteis**: TEM_INS, UMD_INS, VEN_VEL, VEN_DIR, CHUVA

### BDQueimadas INPE — Fallback
- **URL**: `https://queimadas.dgi.inpe.br/queimadas/bdqueimadas/...`
- **Frequência**: 1x/dia (consolidado)
- **Nota**: API não-oficial, pode mudar formato sem aviso

### Sentinel Hub — NDVI
- **Produto**: Sentinel-2 L2A, banda B08 (NIR) e B04 (RED)
- **NDVI**: `(NIR - RED) / (NIR + RED)`
- **Frequência**: cada 5 dias (órbita + filtro de nuvem)
- **API**: Process API via OAuth2

---

*Atualize este documento sempre que descobrir um novo hurdle, tomar uma decisão de design, ou mudar a arquitetura.*