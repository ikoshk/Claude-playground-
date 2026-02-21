# IT Maturity Assessment MVP

An automated tool that assesses a company's IT maturity across **6 dimensions and 15 sub-questions**, using only publicly available data published in 2023–2025.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          IT Maturity Assessment                          │
├─────────────┬─────────────┬──────────────┬───────────────┬──────────────┤
│  Stage 1    │   Stage 2   │   Stage 3    │   Stage 4     │   Stage 5    │
│  Evidence   │  Evidence   │   LLM        │  Deterministic│  Rendering   │
│  Collection │  Filtering  │  Extraction  │  Scoring      │  & Artifacts │
│             │             │              │               │              │
│ Search API  │  Recency    │  Structured  │  Evidence     │  HTML report │
│ Web crawler │  Dedup      │  JSON output │  validation   │  PDF export  │
│ PDF extract │  Coverage   │  per Q1-Q15  │  Scoring      │  PNG visuals │
│ Job signals │  map        │              │  engine       │  Validator   │
└─────────────┴─────────────┴──────────────┴───────────────┴──────────────┘
```

---

## Quick Start (Demo Mode – No API Keys Required)

```bash
# Clone and start
git clone <repo>
cd <repo>

# Start in demo mode (stub search + deterministic demo LLM responses)
make demo

# App available at: http://localhost:8000
```

---

## Full Setup (With Real API Keys)

```bash
# 1. Copy and edit environment variables
cp .env.example .env

# 2. Set your keys in .env:
#    SEARCH_PROVIDER=tavily   (or serpapi / bing)
#    TAVILY_API_KEY=tvly-...
#    LLM_MODE=live
#    LLM_API_KEY=sk-...
#    LLM_MODEL=gpt-4o

# 3. Start services
docker compose up --build

# 4. Open: http://localhost:8000
```

---

## 6 Dimensions & 15 Questions

| ID  | Dimension               | Questions |
|-----|-------------------------|-----------|
| D1  | IT Strategy & Governance | Q1-Q4    |
| D2  | Architecture & Innovation | Q5-Q7   |
| D3  | IT Business Management  | Q8-Q9    |
| D4  | Product Delivery        | Q10-Q11  |
| D5  | Security & Risk         | Q12-Q13  |
| D6  | Methods & Tools         | Q14-Q15  |

---

## Maturity Levels (Fixed)

| Level | Score |
|-------|-------|
| Initial | 1 |
| In development | 2 |
| Industrialized | 3 |
| State of the art | 4 |

---

## Report Outputs

| Artifact | Description |
|----------|-------------|
| `report.html` | Full executive report with all sections A-E |
| `report.pdf` | PDF version (via Playwright) |
| `maturity_visual.png` | 6-dimension maturity blocks |
| `key_takeaways.png` | Top 5 action items with citations |

---

## Critical Constraints

- **Only public sources** - no private data, no inference beyond evidence
- **2023-2025 window only** - out-of-window sources excluded from scoring
- **Maturity levels are fixed** - LLM proposes, deterministic engine decides
- **No partial results** - report returned only when complete and validated
- **No clarifying questions** - runs fully automatically after company name entry

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARCH_PROVIDER` | `stub` | `stub` / `tavily` / `serpapi` / `bing` |
| `LLM_MODE` | `demo` | `demo` (mock) / `live` (real LLM) |
| `LLM_API_KEY` | - | OpenAI-compatible API key |
| `LLM_MODEL` | `gpt-4o` | Any OpenAI-compatible model |
| `TAVILY_API_KEY` | - | Tavily search key |
| `CACHE_TTL_DAYS` | `7` | Days to cache completed assessments |
| `RATE_LIMIT_PER_IP` | `5` | Max requests per IP per hour |
| `EVIDENCE_WINDOW_START` | `2023` | Start year for evidence window |
| `EVIDENCE_WINDOW_END` | `2025` | End year for evidence window |

---

## Services (Docker Compose)

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI application |
| `worker` | - | Celery assessment worker |
| `postgres` | 5432 | PostgreSQL (metadata + run state) |
| `redis` | 6379 | Broker + result backend |
| `flower` | 5555 | Celery monitoring (optional) |

Start with monitoring: `docker compose --profile monitoring up`

---

## Local Development (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Set environment
cp .env.example .env
# Edit .env: set DATABASE_URL to local postgres, REDIS_URL to local redis

# Run API
make dev

# Run worker (separate terminal)
make worker
```

---

## Project Structure

```
backend/
  main.py              FastAPI app
  config.py            Settings
  models.py            Pydantic + SQLAlchemy models
  db.py                Database setup
  orchestrator.py      Pipeline orchestrator
  tasks.py             Celery tasks
  collectors/
    base.py            SearchProvider interface
    search_provider.py Stub + Tavily + SerpAPI + Bing
    crawler.py         Web fetcher + date extraction
    pdf.py             PDF extraction (pdfplumber/pypdf)
    jobs.py            Job posting signals
  analysis/
    rubric.py          Q1-Q15 rubric (single source of truth)
    extractor.py       LLM extraction + demo mode
    scorer.py          Deterministic scoring engine
    validator.py       Report validator
  rendering/
    report_template.html  Jinja2 HTML template
    renderer.py        HTML + PDF renderer
    visuals.py         Matplotlib image generator
  storage/
    repository.py      DB + filesystem persistence
frontend/
  index.html           Single-page UI
docker-compose.yml
Dockerfile
Makefile
requirements.txt
.env.example
```