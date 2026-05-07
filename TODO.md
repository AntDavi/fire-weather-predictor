# TODO.md — Fire Weather Predictor
> Roadmap de 4–5 semanas. Siga a ordem das semanas.
> Cada issue tem: estimativa, dependências, critério de aceite.

---

## Como Usar Este Arquivo

1. **Escolha a próxima issue não concluída** (em ordem)
2. **Leia CLAUDE.md antes** (seção relevante indicada em cada issue)
3. **Peça ao agente com o template de prompt** (seção ao final de cada issue)
4. **Revise o plano antes de aprovar**
5. **Marque como concluída** com `[x]` quando CI passar

**Status**: `[ ]` pendente · `[~]` em progresso · `[x]` concluída

---

## SEMANA 1 — Fundação (Setup, Infra, CI)

### Issue #1.1 — Estrutura Base do Repositório
**Tempo estimado**: 30 min  
**Dependências**: nenhuma  
**Leia no CLAUDE.md**: Seção 7 (Estrutura de Diretórios)

**O que fazer**:
- Criar estrutura de diretórios conforme CLAUDE.md Seção 7
- Criar `.gitignore` adequado para Python/Node/env
- Criar `.env.example` com todas as variáveis (CLAUDE.md Seção 11)
- Criar `README.md` com descrição, setup e badges CI
- Primeiro commit: `chore: estrutura base do repositório`

**Critério de aceite**:
- [X] Estrutura de diretórios criada corretamente
- [X] `.gitignore` cobre Python, `.env`, `__pycache__`, `.pytest_cache`
- [X] `.env.example` com todas as variáveis documentadas
- [X] `README.md` com instruções mínimas de setup

---

### Issue #1.2 — Docker e Docker Compose
**Tempo estimado**: 1.5h  
**Dependências**: #1.1  
**Leia no CLAUDE.md**: Seção 3 (Stack), Seção 7 (Estrutura)

**O que fazer**:
- `Dockerfile` para o backend Python (base: `python:3.11-slim`)
- `docker-compose.yml` com 4 serviços: PostgreSQL 15, Redis 7, Backend, Frontend (nginx simples)
- PostgreSQL com extensão PostGIS habilitada no init
- Health checks em todos os serviços
- Backend só sobe quando DB está healthy (`depends_on: condition: service_healthy`)
- `docker-compose.prod.yml` com variáveis de ambiente externas (sem valores hardcoded)

**Critério de aceite**:
- [ ] `docker compose up` sobe todos os serviços sem erro
- [ ] `docker compose ps` mostra todos como "healthy"
- [ ] PostgreSQL acessível em `localhost:5432`
- [ ] Redis acessível em `localhost:6379`
- [ ] Backend responde em `localhost:8000/health` com `{"status": "ok"}`

---

### Issue #1.3 — GitHub Actions CI
**Tempo estimado**: 1h  
**Dependências**: #1.2  
**Leia no CLAUDE.md**: Seção 15 (Script CI)

**O que fazer**:
- `.github/workflows/ci.yml` que executa no push para `main` e em PRs
- Jobs: `lint` (ruff), `security` (bandit), `test` (pytest com PostgreSQL + Redis como services)
- Cache de dependências pip para velocidade
- Badge CI no README.md
- `scripts/ci.sh` funcional localmente (espelha o Actions)

**Critério de aceite**:
- [ ] Push para `main` dispara o workflow
- [ ] Lint, security scan e testes passam
- [ ] Tempo total do CI < 3 minutos
- [ ] Badge verde no README
- [ ] `bash scripts/ci.sh` funciona localmente

---

### Issue #1.4 — Schema PostgreSQL e Migrations
**Tempo estimado**: 2h  
**Dependências**: #1.2  
**Leia no CLAUDE.md**: Seção 4 (Schema)

**O que fazer**:
- Configurar Alembic para migrations
- Criar migration inicial com as 6 tabelas do CLAUDE.md Seção 4
- Todos os índices geoespaciais (GIST) e de série temporal
- Models SQLAlchemy correspondentes em `app/models/`
- `database.py` com engine async (asyncpg)

**Critério de aceite**:
- [ ] `alembic upgrade head` cria todas as tabelas sem erro
- [ ] `alembic downgrade base` reverte completamente
- [ ] `\d+ weather_stations` mostra coluna `location` como `geometry`
- [ ] Índice GIST confirmado em `hotspots.location` e `fire_history.location`
- [ ] Testes: `test_models.py` verifica que cada model pode ser instanciado e salvo

---

### Issue #1.5 — FastAPI Base + Health Endpoint
**Tempo estimado**: 1h  
**Dependências**: #1.4  
**Leia no CLAUDE.md**: Seção 5 (Endpoints)

**O que fazer**:
- `app/main.py` com FastAPI configurado (CORS, lifespan, docs)
- `app/config.py` com pydantic-settings carregando `.env`
- Endpoint `GET /health` retornando status do DB, Redis e última atualização de dados
- Schemas Pydantic para response de `/health`
- Testes de integração para `/health`

**Critério de aceite**:
- [ ] `GET /health` retorna 200 com DB e Redis conectados
- [ ] `GET /health` retorna 503 se DB ou Redis estiver down (teste com serviço parado)
- [ ] Swagger UI acessível em `/docs`
- [ ] `test_health.py`: testa 200 e 503
- [ ] CI verde

---

## SEMANA 2 — Coleta de Dados

### Issue #2.1 — Collector INMET (Dados Meteorológicos)
**Tempo estimado**: 3h  
**Dependências**: #1.4  
**Leia no CLAUDE.md**: Seção 16 (INMET)

**O que fazer**:
- `app/collectors/inmet_collector.py` — classe `InmetCollector`
- Método `fetch_stations_ceara()`: busca lista de estações automáticas no CE via API INMET
- Método `fetch_readings(station_code, start_date, end_date)`: busca leituras horárias
- Método `sync_recent(hours=24)`: atualiza últimas 24h para todas as estações do CE
- Persistência no banco (upsert em `weather_readings`)
- Fallback: se estação offline, usar estação mais próxima (ST_Distance)
- Tratamento de erros: timeout, rate limit, dados faltantes

**Critério de aceite**:
- [ ] `InmetCollector().sync_recent()` popula `weather_readings` sem erro
- [ ] Upsert funciona (rodar duas vezes não duplica registros)
- [ ] Fallback para estação mais próxima funciona (mock da estação principal offline)
- [ ] Testes: mock da API INMET, testa parsing, testa persistência, testa fallback
- [ ] Cobertura de testes ≥ 80% no módulo
- [ ] CI verde

---

### Issue #2.2 — Collector FIRMS (Hotspots NASA)
**Tempo estimado**: 3h  
**Dependências**: #1.4  
**Leia no CLAUDE.md**: Seção 12 (Hurdles), Seção 16 (FIRMS)

**ATENÇÃO — HURDLE ATIVO**: Endpoint `country` está INDISPONÍVEL. Usar APENAS o endpoint `area/csv` com bbox do Ceará.

**O que fazer**:
- `app/collectors/firms_collector.py` — classe `FirmsCollector`
- Bbox Ceará: `lon_min=-41.5, lat_min=-7.9, lon_max=-37.2, lat_max=-2.7`
- Método `fetch_hotspots(days=1)`: busca VIIRS SNPP NRT para o bbox
- Parse do CSV retornado pela API
- Filtro por `confidence >= nominal` (configurável via env `MIN_HOTSPOT_CONFIDENCE`)
- Persistência em `hotspots` (source='FIRMS_VIIRS')
- Log claro quando API retorna vazio vs. quando falha

**Critério de aceite**:
- [ ] `FirmsCollector().fetch_hotspots()` retorna lista de hotspots ou lista vazia
- [ ] Nunca usa o endpoint `country` (assertion no teste)
- [ ] Filtro de confidence funciona corretamente
- [ ] Upsert sem duplicatas (mesmo hotspot em runs diferentes)
- [ ] Testes: mock do CSV real da API, testa parsing, testa filtro de confidence
- [ ] CI verde

---

### Issue #2.3 — Collector BDQueimadas INPE (Fallback)
**Tempo estimado**: 2.5h  
**Dependências**: #2.2  
**Leia no CLAUDE.md**: Seção 12 (Hurdles), Seção 16 (BDQueimadas)

**O que fazer**:
- `app/collectors/bdqueimadas_collector.py` — classe `BDQueImadasCollector`
- Investigar e documentar a API (pode exigir engenharia reversa do site)
- Método `fetch_queimadas(date_str)`: busca queimadas do dia
- Persistência em `hotspots` (source='INPE')
- Integrar como fallback no `FirmsCollector`: se FIRMS falhar, tentar BDQueimadas
- Degraded mode: se ambos falharem, logar warning e usar dados das últimas 24h do banco

**Critério de aceite**:
- [ ] `BDQueImadasCollector().fetch_queimadas()` retorna dados ou empty list
- [ ] Fallback automático do FIRMS para BDQueimadas funciona (mock FIRMS 500)
- [ ] Degraded mode ativado quando ambos falham (log de warning verificado no teste)
- [ ] Testes: testa fallback chain completo (FIRMS ok, FIRMS fail + INPE ok, ambos fail)
- [ ] CI verde

---

### Issue #2.4 — Collector Sentinel-2 (NDVI)
**Tempo estimado**: 3h  
**Dependências**: #1.4  
**Leia no CLAUDE.md**: Seção 12 (Hurdles — nuvens), Seção 16 (Sentinel Hub)

**O que fazer**:
- `app/collectors/sentinel_collector.py` — classe `SentinelCollector`
- Auth OAuth2 com Sentinel Hub (client credentials flow)
- Método `fetch_ndvi(bbox, date)`: busca mosaico NDVI para área/data
- Filtragem de pixels com cobertura de nuvem > 30%
- Estratégia de fallback para nuvem: usar leitura anterior (máx 5 dias)
- Persistência em `ndvi_readings`
- Métodos: `get_latest_ndvi(lat, lon)` retorna valor mais recente válido

**Critério de aceite**:
- [ ] OAuth2 token refresh automático funciona
- [ ] `fetch_ndvi()` persiste leituras com `cloud_coverage_pct`
- [ ] Fallback para leitura anterior (≤ 5 dias) quando nuvem > 30%
- [ ] Retorna `None` se não houver leitura válida nos últimos 5 dias (não quebra o sistema)
- [ ] Testes: mock da Sentinel API, testa fallback de nuvem
- [ ] CI verde

---

### Issue #2.5 — Backfill Histórico INPE (2003–2024)
**Tempo estimado**: 2h  
**Dependências**: #1.4  
**Leia no CLAUDE.md**: Seção 4 (tabela fire_history)

**O que fazer**:
- `scripts/backfill_history.py` — script one-time (não é um serviço contínuo)
- Download e parse dos dados históricos do INPE BDQueimadas (CSV ou shapefile)
- Inserção em lotes (batch insert de 1000 registros) na tabela `fire_history`
- Filtro por estado='CE' para MVP
- Idempotente: pode ser rodado múltiplas vezes sem duplicar dados
- Log de progresso (quantos registros inseridos, tempo estimado)

**Critério de aceite**:
- [ ] Script roda em < 30 min para dados do CE
- [ ] `SELECT COUNT(*) FROM fire_history WHERE state='CE'` retorna valor > 0
- [ ] Rodado duas vezes não duplica (UNIQUE constraint ou ON CONFLICT DO NOTHING)
- [ ] Script documentado no README com instruções de uso

---

## SEMANA 3 — ML e API Core

### Issue #3.1 — Calculadora FWI
**Tempo estimado**: 2.5h  
**Dependências**: #2.1  
**Leia no CLAUDE.md**: Seção 6 (Feature Engineering — FWI)

**O que fazer**:
- `app/ml/fwi_calculator.py` — implementação do FWI canadense
- Funções puras: `calculate_ffmc()`, `calculate_dmc()`, `calculate_dc()`, `calculate_isi()`, `calculate_bui()`, `calculate_fwi()`
- Cada função recebe dados meteorológicos e retorna o índice correspondente
- Valores padrão iniciais para "startup" (primeiros cálculos do dia)
- Validação de inputs (temperatura, umidade, vento, precipitação dentro de ranges válidos)

**Critério de aceite**:
- [ ] Resultados validados contra tabelas de referência do Canadian Forest Service
- [ ] Testes unitários com valores conhecidos (ex: temp=25, humid=50, wind=20 → FWI esperado)
- [ ] Todos os testes passam com tolerância de ±0.5 nos resultados
- [ ] Cobertura de testes ≥ 90% (funções matemáticas são determinísticas)
- [ ] CI verde

---

### Issue #3.2 — Feature Engineering
**Tempo estimado**: 2h  
**Dependências**: #3.1, #2.1, #2.2, #2.4  
**Leia no CLAUDE.md**: Seção 6 (Features do Modelo)

**O que fazer**:
- `app/services/feature_engineer.py` — classe `FeatureEngineer`
- Método `build_features(lat, lon, timestamp)`: retorna dict com todas as features do modelo
- Queries geoespaciais: estação mais próxima, hotspots em raio 50km, histórico local
- Integração com FWI calculator
- Tratamento de features ausentes: valores padrão documentados no código
- Retorna também metadados de freshness (quando foi cada dado)

**Critério de aceite**:
- [ ] `build_features(lat=-3.73, lon=-38.52, timestamp=now)` retorna dict com TODOS os campos do CLAUDE.md Seção 6
- [ ] Queries usam índices GIST (verificar com EXPLAIN ANALYZE no teste)
- [ ] Features ausentes retornam valor default, não exceção
- [ ] Testes: fixtures no banco com dados conhecidos → features esperadas
- [ ] CI verde

---

### Issue #3.3 — Treinamento do Modelo XGBoost
**Tempo estimado**: 3h  
**Dependências**: #3.2, #2.5  
**Leia no CLAUDE.md**: Seção 13 (Decisões — XGBoost + SHAP)

**O que fazer**:
- `scripts/train_model.py` — script de treinamento
- `app/ml/train.py` — funções reutilizáveis de treinamento
- Target: `fired_within_7days` (1 se houve queimada nos 7 dias seguintes, 0 caso contrário)
- Gerado a partir de `fire_history` + dados meteorológicos históricos
- Split temporal: train até 2022, validation 2023, test 2024
- Métricas: AUC-ROC, F1, Precision, Recall, threshold ótimo
- Salvar modelo treinado como `app/ml/model_v1.pkl`
- Notebook `notebooks/model_evaluation.ipynb` com gráficos

**Critério de aceite**:
- [ ] AUC-ROC ≥ 0.75 no conjunto de teste 2024
- [ ] F1-score ≥ 0.65 no conjunto de teste
- [ ] Modelo serializado e carregável via `joblib.load()`
- [ ] SHAP TreeExplainer funciona com o modelo treinado
- [ ] Notebook com curva ROC, feature importance, SHAP summary plot
- [ ] CI verde

---

### Issue #3.4 — Wrapper do Modelo + Predição com SHAP
**Tempo estimado**: 2h  
**Dependências**: #3.3  
**Leia no CLAUDE.md**: Seção 2 (Arquitetura), Seção 5 (Response format)

**O que fazer**:
- `app/ml/model.py` — classe `RiskModel`
- Carrega modelo na inicialização (singleton via FastAPI lifespan)
- Método `predict(features: dict)` retorna `{"risk_probability": float, "risk_level": str, "shap_values": dict}`
- Thresholds: low < 40%, medium < 70%, high >= 70%
- SHAP values para as top-5 features mais influentes
- Versão do modelo no response

**Critério de aceite**:
- [ ] `RiskModel().predict(features)` retorna estrutura esperada
- [ ] Thresholds corretos: `risk_level` bate com `risk_probability`
- [ ] SHAP values são calculados e retornam top-5 features
- [ ] Modelo é carregado uma vez (singleton, não a cada request)
- [ ] Testes: predição com features conhecidas → risco esperado
- [ ] CI verde

---

### Issue #3.5 — Endpoint /api/v1/risk
**Tempo estimado**: 2.5h  
**Dependências**: #3.4, #3.2  
**Leia no CLAUDE.md**: Seção 5 (Endpoints), Seção 14 (Cache)

**O que fazer**:
- `app/routers/risk.py` — endpoint `GET /api/v1/risk`
- Parâmetros: `lat` (float), `lon` (float), `radius_km` (float, default=20, max=100)
- Fluxo: cache lookup → feature engineering → predição → cache set → response
- Response em formato GeoJSON (CLAUDE.md Seção 5)
- Cache com TTL 3600s (key baseada em lat/lon arredondados a 3 casas)
- Validação de parâmetros (lat entre -90/90, lon entre -180/180)
- Persistência da predição em `risk_predictions`

**Critério de aceite**:
- [ ] `GET /api/v1/risk?lat=-3.73&lon=-38.52&radius_km=20` retorna GeoJSON válido
- [ ] Response contém `risk_probability`, `risk_level`, `shap_values`, `data_freshness`
- [ ] Segunda request idêntica vem do cache (header `X-Cache: HIT`)
- [ ] Parâmetros inválidos retornam 422 com mensagem clara
- [ ] Testes: response schema, cache hit, validação de params
- [ ] CI verde

---

### Issue #3.6 — Endpoints /hotspots e /weather
**Tempo estimado**: 2h  
**Dependências**: #3.5  
**Leia no CLAUDE.md**: Seção 5 (Endpoints)

**O que fazer**:
- `app/routers/hotspots.py` — `GET /api/v1/hotspots`
- `app/routers/weather.py` — `GET /api/v1/weather`
- Hotspots: lista de hotspots recentes em `radius_km`, filtro por `hours_back`
- Weather: dados da estação mais próxima (ST_Distance)
- Cache para ambos (TTLs do CLAUDE.md Seção 14)

**Critério de aceite**:
- [ ] Ambos endpoints retornam dados corretos com fixtures no banco
- [ ] Queries usam índices geoespaciais (EXPLAIN ANALYZE verificado)
- [ ] Cache funcionando com TTLs corretos
- [ ] Testes de integração para ambos
- [ ] CI verde

---

## SEMANA 4 — Frontend, Deploy e Validação

### Issue #4.1 — Frontend Leaflet.js
**Tempo estimado**: 3h  
**Dependências**: #3.5, #3.6  
**Leia no CLAUDE.md**: Seção 2 (Arquitetura — Frontend)

**O que fazer**:
- `frontend/index.html` + `frontend/style.css` + `frontend/app.js`
- Mapa Leaflet.js centrado no Ceará (lat=-5.5, lon=-39.5, zoom=7)
- Input: campos de lat, lon, raio com botão "Verificar Risco"
- Pins coloridos: verde (low), amarelo (medium), vermelho (high)
- Popup ao clicar: probabilidade, nível, top-3 fatores SHAP, freshness dos dados
- Layer de hotspots recentes (últimas 24h) em laranja
- Loading state durante request
- Error state se API falhar

**Critério de aceite**:
- [ ] Página carrega sem erro no browser
- [ ] Mapa renderiza com Ceará centralizado
- [ ] Busca com coordenadas reais retorna pin colorido correto
- [ ] Popup mostra todos os campos do response
- [ ] Hotspots visíveis como layer separado
- [ ] Funciona em mobile (responsive básico)

---

### Issue #4.2 — Scheduler de Coleta (Background Tasks)
**Tempo estimado**: 2h  
**Dependências**: #2.1, #2.2, #2.3, #2.4  

**O que fazer**:
- `app/scheduler.py` — usando `APScheduler` ou `asyncio` + FastAPI lifespan
- Job `collect_weather`: a cada 1 hora → `InmetCollector().sync_recent(hours=2)`
- Job `collect_hotspots`: a cada 3 horas → `FirmsCollector().fetch_hotspots(days=1)`
- Job `collect_ndvi`: 1x/dia às 02:00 → `SentinelCollector().fetch_ndvi(...)`
- Jobs rodam assincronamente, não bloqueiam requests
- Logs estruturados para cada execução (início, fim, registros processados, erros)

**Critério de aceite**:
- [ ] Scheduler inicia junto com a aplicação (no lifespan)
- [ ] Jobs executam nos intervalos corretos (verificado via logs)
- [ ] Falha em um job não derruba os outros nem a aplicação
- [ ] Testes: mock dos collectors, verificar que jobs são agendados
- [ ] CI verde

---

### Issue #4.3 — Deploy no Railway/Fly.io
**Tempo estimado**: 2.5h  
**Dependências**: #4.1, #4.2  

**O que fazer**:
- `docker-compose.prod.yml` sem valores hardcoded (apenas referências a env vars)
- Variáveis de ambiente configuradas no Railway/Fly.io
- `alembic upgrade head` executado automaticamente no startup
- HTTPS automático (Railway/Fly.io provêm)
- Verificar headers de segurança básicos (CORS configurado corretamente)
- Script de rollback documentado

**Critério de aceite**:
- [ ] `curl https://sua-app.railway.app/health` retorna 200
- [ ] HTTPS funcionando (sem warnings no browser)
- [ ] Todos os endpoints funcionais em produção
- [ ] Logs acessíveis no dashboard do Railway/Fly.io
- [ ] Rollback testado (redeploy da versão anterior funciona)

---

### Issue #4.4 — Backtest de Validação (2023)
**Tempo estimado**: 3h  
**Dependências**: #3.3, #2.5  
**Leia no CLAUDE.md**: Seção 13 (Decisões — XGBoost)

**O que fazer**:
- `notebooks/model_evaluation.ipynb` — seção de backtest
- Simular predições para cada semana de 2023 usando dados disponíveis até aquela data
- Comparar predições com queimadas reais (fire_history)
- Métricas por mês: precision, recall, F1, falsos positivos críticos
- Mapa de calor: predições vs. realidade para CE 2023
- Seção de discussão: onde o modelo acertou, onde errou, limitações

**Critério de aceite**:
- [ ] Notebook roda sem erros do início ao fim
- [ ] Métricas de 2023 documentadas (AUC-ROC, F1 por mês)
- [ ] Pelo menos 3 figuras: curva ROC, mapa de erro, feature importance temporal
- [ ] Seção de limitações honesta e documentada

---

## SEMANA 5 — Paper Científico

### Issue #5.1 — Estrutura do Paper
**Tempo estimado**: 2h  
**Dependências**: todas as anteriores  

**Seções obrigatórias** (20–25 páginas, ABNT):
1. Introdução (problema, motivação, objetivos, contribuições)
2. Trabalhos Relacionados (5+ papers: FWI, ML para incêndios, sistemas similares)
3. Metodologia (arquitetura, fontes de dados, feature engineering, modelo)
4. Resultados (métricas, backtest, exemplos reais)
5. Discussão (limitações, trabalhos futuros)
6. Conclusão
7. Referências (30+ referências, formato ABNT)

**Critério de aceite**:
- [ ] Estrutura de seções criada no documento
- [ ] 30+ referências identificadas e listadas
- [ ] Figuras planejadas (diagrama de arquitetura, mapas, curvas ROC)

---

### Issue #5.2 — Figuras e Diagramas para o Paper
**Tempo estimado**: 3h  
**Dependências**: #4.4  

**O que fazer**:
- Diagrama de arquitetura do sistema (exportar como PNG/SVG)
- Mapa do Ceará com exemplo de predições (screenshot da aplicação)
- Curva ROC do modelo no conjunto de teste 2024
- SHAP summary plot (feature importance)
- Mapa de backtest 2023 (predições vs. realidade)

**Critério de aceite**:
- [ ] Todas as 5 figuras geradas em alta resolução (≥ 300 DPI para impressão)
- [ ] Figuras com legendas e labels em português
- [ ] Prontas para inserção no documento ABNT

---

### Issue #5.3 — Escrita do Paper Completo
**Tempo estimado**: 10h  
**Dependências**: #5.1, #5.2  

**Critério de aceite**:
- [ ] Documento final com 20–25 páginas
- [ ] Todas as seções completas com texto original
- [ ] 30+ referências formatadas em ABNT
- [ ] Todas as figuras inseridas com legendas
- [ ] Revisão ortográfica e gramatical
- [ ] Abstract em português e inglês

---

## Issues Técnicas de Qualidade (Qualquer Semana)

### Issue #Q.1 — Logging Estruturado
**Tempo estimado**: 1h  
**Quando fazer**: Semana 2 ou 3

- Configurar `structlog` ou logging padrão com formato JSON
- Campos obrigatórios: `timestamp`, `level`, `module`, `function`, `message`, `extra`
- Log de todas as chamadas de API externas (latência, status)
- Log de todas as predições (lat, lon, risk_level, model_version)

---

### Issue #Q.2 — Rate Limiting e Proteção Básica
**Tempo estimado**: 1h  
**Quando fazer**: Antes do deploy

- `slowapi` para rate limiting: 60 requests/min por IP
- Headers de segurança via middleware: `X-Content-Type-Options`, `X-Frame-Options`
- CORS configurado explicitamente (não `*` em produção)

---

### Issue #Q.3 — Documentação da API
**Tempo estimado**: 1h  
**Quando fazer**: Semana 3 ou 4

- Docstrings completas em todos os endpoints (aparecem no Swagger)
- Exemplos de request/response no Swagger
- `POST /api/v1/risk/batch` documentado com limite de 10 items

---

## Resumo de Esforço

| Semana | Issues | Horas Estimadas |
|--------|--------|----------------|
| 1 | #1.1 – #1.5 | ~6h |
| 2 | #2.1 – #2.5 | ~14h |
| 3 | #3.1 – #3.6 | ~14h |
| 4 | #4.1 – #4.4 | ~11h |
| 5 | #5.1 – #5.3 | ~15h |
| Qualidade | #Q.1 – #Q.3 | ~3h |
| **TOTAL** | **22 issues** | **~63h** |

**Com Claude Code (redução ~40%)**: ~38h efetivas

---

## Template de Prompt Para Claude Code

Use este template antes de cada issue:

```
Vamos implementar Issue #X.Y: [nome da issue]

Contexto: Projeto Fire Weather Predictor — API de detecção de queimadas
Leia CLAUDE.md na raiz, especialmente as seções [X] e [Y]

ANTES de escrever qualquer código, responda:
1. [pergunta específica sobre o plano]
2. [pergunta sobre dependências]
3. [pergunta sobre testes]
4. [pergunta sobre edge cases]

Restrições obrigatórias (CLAUDE.md Seção 9):
- [restrição relevante para esta issue]
- Rode scripts/ci.sh antes de declarar concluído
- Testes obrigatórios para cada função pública

Aguarde minha aprovação do plano antes de codificar.
```

---

*Atualize o status das issues com `[x]` conforme concluir. Adicione novas issues aqui se surgir trabalho não previsto.*