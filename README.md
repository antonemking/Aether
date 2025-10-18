# Aether - Production RAG Observability Platform

> **PRIVATE REPOSITORY** - Aether backend and infrastructure

Aether is a production-focused RAG (Retrieval-Augmented Generation) observability platform that provides real-time monitoring, evaluation, and alerting for AI applications.

## Key Differentiator

**LangSmith is for development debugging. Aether is for production monitoring.**

- ✅ **Production Alerting** - Slack notifications for hallucinations, cost spikes, latency issues
- ✅ **LLM-based Evaluation** - RAGAS faithfulness scoring detects hallucinations automatically
- ✅ **Cost Tracking** - Monitor evaluation costs per trace
- ✅ **Performance Monitoring** - P95 latency, trace volume, hallucination rates
- ✅ **Alert Management** - Configure thresholds, view history, mark resolved

## Repository Structure

```
aether/
├── aether-api/          # FastAPI backend (THIS REPO - PRIVATE)
├── aether-sdk-python/   # Python SDK (SEPARATE PUBLIC REPO)
└── aether-web/          # Next.js dashboard (TO BE BUILT)
```

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 14+
- Redis 6+
- OpenAI API key (for RAGAS evaluation)

### Setup

1. **Install PostgreSQL and Redis:**
```bash
brew install postgresql@14 redis
brew services start postgresql@14
brew services start redis
```

2. **Create database:**
```bash
createdb aether
```

3. **Install Python dependencies:**
```bash
cd aether-api
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings:
# - DATABASE_URL
# - REDIS_URL
# - OPENAI_API_KEY (for RAGAS)
```

5. **Run migrations:**
```bash
alembic upgrade head
```

6. **Seed test data:**
```bash
python seed_data.py
```

### Running the Application

**Start API server:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Start evaluation worker:**
```bash
python run_worker_once.py
```

**API Documentation:**
- Interactive docs: http://127.0.0.1:8000/docs
- OpenAPI spec: http://127.0.0.1:8000/openapi.json

## Core Features

### 1. Trace Ingestion

Ingest RAG query/response traces with contexts:

```bash
curl -X POST http://localhost:8000/api/v1/traces/ \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "...",
    "query": "What is the capital of France?",
    "response": "Paris is the capital of France.",
    "contexts": [
      {"text": "Paris is the capital...", "source": "doc_001", "score": 0.95}
    ],
    "token_count": 150,
    "latency_ms": 850,
    "cost_usd": 0.002
  }'
```

### 2. Automatic Evaluation

The evaluation worker automatically:
- Computes faithfulness score (RAGAS + OpenAI)
- Calculates token overlap ratio
- Detects hallucinations (faithfulness < 0.5)
- Tracks evaluation costs

### 3. Production Alerting

Configure Slack alerts per project:

```bash
curl -X PUT http://localhost:8000/api/v1/alert-config/{project_id} \
  -H "Content-Type: application/json" \
  -d '{
    "slack_webhook_url": "https://hooks.slack.com/services/...",
    "slack_enabled": true,
    "hallucination_threshold": 0.5,
    "hallucination_alerts_enabled": true,
    "daily_cost_budget_usd": 10.0,
    "cost_spike_alerts_enabled": true,
    "latency_p95_threshold_ms": 3000,
    "latency_alerts_enabled": true
  }'
```

See [docs/SLACK_ALERTING.md](aether-api/docs/SLACK_ALERTING.md) for full setup guide.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENT APP                          │
│              (using aether-sdk-python)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ POST /api/v1/traces/
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      AETHER API                             │
│                    (FastAPI)                                │
└────────┬─────────────────────────────────────┬──────────────┘
         │                                     │
         │ Save trace                          │ Queue job
         ▼                                     ▼
    ┌─────────┐                           ┌──────────┐
    │PostgreSQL│                           │  Redis   │
    │ Database│                           │  Queue   │
    └─────────┘                           └─────┬────┘
         ▲                                      │
         │                                      │ BRPOP
         │ Save evaluation                      ▼
         │                          ┌────────────────────────┐
         │                          │  Evaluation Worker      │
         │                          │  - Compute metrics      │
         └──────────────────────────│  - RAGAS faithfulness   │
                                    │  - Check alerts         │
                                    └──────────┬──────────────┘
                                               │
                                               │ Send alerts
                                               ▼
                                         ┌──────────┐
                                         │  Slack   │
                                         └──────────┘
```

## Database Schema

- **organizations** - Customer accounts with plan types
- **projects** - RAG systems (customers can have multiple)
- **users** - Dashboard access
- **rag_traces** - Query/response interactions with contexts
- **evaluations** - Computed metrics for each trace
- **alerts** - Alert history
- **alert_configs** - Per-project alert configuration

## Development

### Testing

```bash
# Test trace ingestion
python test_trace_ingestion.py

# Test RAGAS faithfulness
python test_ragas_faithfulness.py

# Test Slack integration (requires webhook URL)
python test_slack_integration.py
```

### Adding New Metrics

1. Add metric to `app/workers/evaluator.py` in `run_evaluations()`
2. Add field to `Evaluation` model in `app/models/evaluation.py`
3. Create migration: `alembic revision --autogenerate -m "add_metric"`
4. Apply migration: `alembic upgrade head`

### Adding New Alert Types

1. Add type to `AlertType` enum in `app/models/alert.py`
2. Add formatter to `SlackService` in `app/services/slack_service.py`
3. Add check logic to `check_and_send_alerts()` in `app/workers/evaluator.py`

## Production Deployment

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/aether

# Redis
REDIS_URL=redis://host:6379/0

# API Security
API_SECRET_KEY=your-secret-key-here
API_ALGORITHM=HS256

# OpenAI (for evaluations)
OPENAI_API_KEY=sk-...

# Environment
ENVIRONMENT=production

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

### Scaling

**API Server:**
- Run multiple uvicorn workers behind Nginx/Caddy
- Use Supabase PostgreSQL for managed database
- Use Redis Cloud for managed queue

**Evaluation Workers:**
- Run multiple worker processes (one per CPU core)
- Each worker polls the same Redis queue (workers compete for jobs)
- Scale horizontally as evaluation volume increases

**Cost Optimization:**
- Use RAGAS smart sampling (only evaluate X% of traces)
- Cache evaluation results to avoid re-computing
- Consider cheaper LLMs for non-critical metrics

## SDK Integration

The Python SDK will be open source and published to PyPI:

```python
from aether import AetherClient

aether = AetherClient(api_key="ae_...")

# Decorator for LLM calls
@aether.trace(project_id="...")
def ask_llm(query: str) -> str:
    contexts = retriever.search(query)
    response = llm.generate(query, contexts)
    return response

# Or manual tracing
with aether.trace_span(project_id="...", query=query) as span:
    contexts = retriever.search(query)
    span.add_contexts(contexts)
    response = llm.generate(query, contexts)
    span.set_response(response)
```

## Roadmap

### Phase 1: MVP (Week 1-2) ✅
- [x] FastAPI backend infrastructure
- [x] Trace ingestion and storage
- [x] Evaluation worker with RAGAS
- [x] Slack alerting system
- [x] Alert configuration and management APIs

### Phase 2: Advanced Evaluation (Week 3-4)
- [ ] Additional RAGAS metrics (relevancy, context recall)
- [ ] PII detection
- [ ] Toxicity scoring
- [ ] Custom evaluation functions
- [ ] Smart sampling strategies

### Phase 3: Python SDK (Week 5-6)
- [ ] Decorator-based instrumentation
- [ ] LangChain integration
- [ ] LlamaIndex integration
- [ ] Async support
- [ ] Batch ingestion

### Phase 4: Dashboard (Week 7-8)
- [ ] Next.js + shadcn/ui
- [ ] Traces explorer with filters
- [ ] Metrics dashboard
- [ ] Alert management UI
- [ ] Project configuration UI

### Phase 5: Production Hardening
- [ ] Authentication (Supabase Auth)
- [ ] Rate limiting
- [ ] API key management
- [ ] Usage quotas by plan
- [ ] Billing integration (Stripe)

## License

**PROPRIETARY** - This repository is private. All rights reserved.

The Python SDK (aether-sdk-python) will be open source under MIT license.

## Support

Internal questions: antone.king@company.com
