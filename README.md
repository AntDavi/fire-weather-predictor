# Fire Weather Predictor

[![CI](https://github.com/AntDavi/fire-weather-predictor/actions/workflows/ci.yml/badge.svg)](https://github.com/AntDavi/fire-weather-predictor/actions/workflows/ci.yml)

API REST para detecção de hotspots de queimadas e predição de risco de incêndio florestal em tempo real.

**Contexto**: 32º Prêmio Jovem Cientista CNPq 2026 — "IA & Meio Ambiente"
**Região**: Ceará, Brasil

## Stack

- **Backend**: FastAPI + PostgreSQL/PostGIS + Redis
- **ML**: XGBoost + SHAP
- **Frontend**: Leaflet.js
- **Deploy**: Docker + Docker Compose

## Setup Rápido

```bash
cp .env.example .env
# Preencha as variáveis em .env

docker compose up --build
```

A API estará disponível em `http://localhost:8000`.
Documentação interativa: `http://localhost:8000/docs`

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Status da API |
| GET | `/api/v1/risk` | Predição de risco por coordenada |
| GET | `/api/v1/hotspots` | Hotspots recentes na área |
| GET | `/api/v1/weather` | Dados meteorológicos |
| POST | `/api/v1/risk/batch` | Predições em lote (máx 10) |

## Desenvolvimento

```bash
# CI local (lint + security + testes)
bash scripts/ci.sh
```