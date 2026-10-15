# MicroCred GenAI Monorepo

**AI-Powered Skills Assessment Platform** with GPT scoring, RAG recommendations, and personalized learning paths.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## Quick Links
- 📚 **[Deployment Guide](RENDER-DEPLOYMENT.md)** - Deploy to Render in 5 minutes
- 📖 **[API Documentation](http://localhost:8000/docs)** - Swagger UI (after running locally)
- 🎨 **[Frontend Guide](docs/FE-GUIDE.md)** - Complete frontend development guide
- **[Deployed:]** microcred-api.onrender.com

## Prerequisites
- Python 3.12.2
- Poetry 1.8.x
- Docker & Docker Compose

## Bootstrap
1. Install dependencies:
   ```bash
   poetry install
   ```
2. Copy environment template and supply secrets:
   ```bash
   cp .env.example .env
   ```
   - Keep `AUTO_PROCESS_JOBS=false` for local work so submissions only enqueue jobs (handled by the worker).
3. Launch backing services along with API and worker:
   ```bash
   docker compose up --build
   ```
4. Run database migrations to install reference data (roles, question templates):
   ```bash
   poetry run alembic upgrade head
   ```

## Local Development
- Run the API without Docker:
  ```bash
  poetry run uvicorn src.api.main:app --reload
  ```
- Start the worker:
  ```bash
  poetry run python -m src.workers.worker
  ```
- Check available tracks:
  ```bash
  curl http://localhost:8000/tracks
  ```
- Start/resume an assessment (requires JWT from `/tests/utils.py` helper or issue_smoke_token):
  ```bash
  curl -H "Authorization: Bearer <token>" \
       -X POST http://localhost:8000/assessments/start \
       -d '{"role_slug": "backend-engineer"}'
  ```
- Submit an assessment payload (omit `responses` to test degraded submissions):
  ```bash
  curl -H "Authorization: Bearer <token>" \
       -X POST http://localhost:8000/assessments/{assessment_id}/submit \
       -d '{
             "responses": [
               {"question_id": "snap-uuid-1", "selected_option": "A"},
               {"question_id": "snap-uuid-2", "answer_text": "Essay text", "metadata": {"source": "ui"}}
             ]
           }'
  ```
- Execute linting and tests:
  ```bash
  scripts/run-tests.sh
  ```
- Refresh OpenAPI schema:
  ```bash
  poetry run python scripts/export_openapi.py
  ```

## Deployment

### 🚀 Deploy to Render (Recommended)
The fastest way to deploy this application to production:

```bash
# 1. Commit deployment config
git add render.yaml scripts/render-build.sh
git commit -m "add Render deployment config"
git push origin main

# 2. Deploy using Blueprint
# Visit: https://render.com
# Click: New + → Blueprint → Select your repo
# Render will auto-detect render.yaml and deploy everything!
```

**Complete deployment guide**: See [RENDER-DEPLOYMENT.md](RENDER-DEPLOYMENT.md)

**Auto job processing**:
- Set `AUTO_PROCESS_JOBS=true` on Render so the API triggers GPT/RAG/Fusion scoring as soon as a submission lands (no worker dyno required).
- Keep the flag `false` locally or when a dedicated worker is running; jobs will still enqueue to Redis and be consumed by `src.workers.worker`.

**What gets deployed:**
- ✅ FastAPI application (free tier)
- ✅ PostgreSQL database (90 days free)
- ✅ Redis cache (free tier)
- ✅ Auto-migrations on deploy
- ✅ SSL certificate included
- ✅ Zero-downtime deployments

### Alternative Deployment Options
- **Docker Compose**: `docker compose up --build`
- **AWS/GCP/Azure**: See deployment guide
- **VPS (DigitalOcean/Linode)**: Manual setup instructions in guide

## Project Structure
Key directories follow the architecture guide:
- `src/api`: FastAPI application and route definitions.
- `src/workers`: RQ worker entrypoint and job handlers.
- `src/domain`: Shared domain models between services.
- `src/infrastructure`: Repositories and data access abstractions.
  - `udemy_courses.csv`: Sample dataset (3,684 courses) for recommendations and RAG features.
- `tests`: Pytest-based unit and integration suites.
- `docs/stories`: Implementation documentation for each user story.

## API Documentation

### SwaggerUI
After starting the API, access interactive documentation at:
- **SwaggerUI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Available Endpoints (Epic 1)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | - | Health check |
| GET | `/tracks` | - | List all active tracks |
| GET | `/tracks/{slug}` | - | Get track by slug |
| POST | `/tracks` | Admin | Create track |
| PATCH | `/tracks/{slug}` | Admin | Update track |
| DELETE | `/tracks/{slug}` | Admin | Soft-delete track |
| GET | `/questions` | - | List questions (filter by role_slug) |
| GET | `/questions/{id}` | - | Get question by ID |
| POST | `/questions` | Admin | Create question |
| PATCH | `/questions/{id}` | Admin | Update question (versioned) |
| DELETE | `/questions/{id}` | Admin | Soft-delete question |
| POST | `/assessments/start` | Student | Start/resume assessment |
| POST | `/assessments/{id}/submit` | Student | Submit for scoring |
| GET | `/assessments/{id}/status` | Student | Get progress status |
| POST | `/assessments/{id}/webhook` | Student | Register webhook URL |

### Available Endpoints (Epic 3)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/assessments/{id}/result` | Student | Get assessment result with recommendations |
| POST | `/assessments/{id}/feedback` | Student | Submit feedback on recommendations |

### Generate Test Token
```python
from src.core.auth import create_access_token

# Student token
token = create_access_token("test-user", roles=["student"])

# Admin token
token = create_access_token("admin-user", roles=["admin"])
```

## Development Guidelines

### For Developers
- **Coding Standards**: See [docs/architecture/coding-standards.md](docs/architecture/coding-standards.md)
- **Script Development**: Always add path setup to scripts (see coding standards)
- **Quality Gates**: Run `poetry run ruff check .` and `poetry run pytest` before committing

### For AI Agents & Copilot
- **Primary Guide**: [docs/architecture/ai-development-guidelines.md](docs/architecture/ai-development-guidelines.md)
- **Quick Reference**: [.github/agents/python-rules.md](.github/agents/python-rules.md)
- **Critical**: All scripts must include `sys.path` setup for module imports

### Before Committing
```bash
# Run quality checks
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest tests/

# If all pass
git add -A
git commit -m "your message"
git push
```

## Implementation Progress

### Epic 1: Role-Gated Assessment Foundation ✅
- [x] Story 1.1: Monorepo Baseline and Auth Skeleton
- [x] Story 1.2: Track Catalog Management
- [x] Story 1.3: Question Bank CRUD and Versioning
- [x] Story 1.4: Role-Gated Assessment Start

### Epic 2: Async Scoring and Persistence Backbone ✅
- [x] Story 2.1: Submission Finalization and Rule Scoring
- [x] Story 2.2: GPT Essay Scoring Worker
- [x] Story 2.3: Status Polling, Webhooks, and Idempotency

### Epic 3: Recommendations, Transparency, and Feedback Loop ✅
- [x] Story 3.1: RAG Retrieval Service
- [x] Story 3.2: Fusion Summary and Result Endpoint
- [x] Story 3.3: Feedback Collection
