# BMAD Agent Context: Python Development Rules

**AUTO-LOAD:** This file is automatically loaded when BMAD agents are activated for Python development tasks.

## CRITICAL RULES - ALWAYS APPLY

### 1. Script Module Import Setup
**EVERY** script in `scripts/` directory **MUST** start with:

```python
from __future__ import annotations

import sys
from pathlib import Path

# REQUIRED: Enable src package imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.module import something  # Now works
```

**Violation Impact:** CI pipeline fails with `ModuleNotFoundError: No module named 'src'`

### 2. SQLAlchemy Reserved Names
**NEVER** use `metadata` as column name. Use this pattern:
```python
metadata_: Mapped[dict] = mapped_column("metadata", JSON)
```

### 3. Code Quality Gates - Run Before Commit
```bash
# MUST run BOTH - they are different!
poetry run ruff check --fix .     # Lint (imports, unused vars)
poetry run ruff format .          # Format (spacing, quotes)

# Verify
poetry run ruff check . && poetry run ruff format --check .

# Tests
poetry run pytest tests/
```
**WARNING:** `ruff check` ≠ `ruff format`! Both must pass for CI.

### 4. Line Length Limit
- Maximum: **100 characters**
- Use parentheses or backslash for multi-line continuation:

```python
# String continuation with backslash
PROMPT = """You are an expert evaluator for a \
micro-credential assessment platform."""

# Assignment with parentheses
self.timeout = (
    timeout_seconds if timeout_seconds else settings.timeout
)

# Long strings in tests/data
response_data = {
    "answer": (
        "First part of the long string "
        "second part of the long string"
    )
}
```

### 5. Import Order (Ruff I001)
```python
from __future__ import annotations  # 1. Future

import sys                           # 2. Stdlib
from pathlib import Path

from fastapi import FastAPI          # 3. Third-party

from src.api import routes           # 4. Local
```
**RUN**: `ruff check --fix .` to auto-sort imports.

### 6. Unused Imports (F401)
- Run `ruff check --fix .` to auto-remove unused imports
- Don't import "just in case"

### 7. Unused Variables (F841)
```python
# BAD
except Exception as e:  # e never used!
    log.error("Failed")

# GOOD
except Exception:
    log.error("Failed")
```

### 8. Undefined Names (F821)
- Always verify class/function is imported before use
- Never use placeholder imports - add TODO comment instead

### 9. Test Fixture Names
- Use `db` for database session (NOT `async_session`)
- Use `test_client` for HTTP client
- Check `conftest.py` for actual fixture names

### 10. Dataclass Required Fields
Include ALL required fields when creating dataclass instances:
```python
# GPTResponse needs ALL fields
GPTResponse(
    content="...",
    model="gpt-4o-mini",
    prompt_tokens=100,
    completion_tokens=50,
    total_tokens=150,      # Required!
    finish_reason="stop",  # Required!
)
```

### 11. Model Field Names
Check actual model definition before creating instances:
```python
# BAD - guessing field names
AssessmentQuestionSnapshot(source_question_id=1)

# GOOD - check model first
AssessmentQuestionSnapshot(question_template_id=1)
```

### 12. Enum Values
Verify enum values exist before using:
```python
# Check the enum definition first!
# JobStatus.QUEUED exists, JobStatus.PENDING doesn't!
job = AsyncJob(status=JobStatus.QUEUED)  # GOOD
```

### 13. Alembic Migration - Enum Names
- PostgreSQL enum names use `snake_case` (e.g., `assessment_status`)
- Check existing enum names before ALTER TYPE

```python
# WRONG: op.execute("ALTER TYPE assessmentstatus ...")
# CORRECT: op.execute("ALTER TYPE assessment_status ...")
```

### 14. Alembic Migration - Avoid Enum Conflicts
- **Use String columns instead of PostgreSQL Enum for new tables**
- SQLAlchemy may ignore `create_type=False` causing duplicate errors

```python
# Use String(20) instead of sa.Enum() to avoid conflicts
sa.Column("job_type", sa.String(20), nullable=False)
sa.Column("status", sa.String(20), server_default="queued")
```

### 15. Local vs Docker Database URL
```bash
# Docker (in .env): @db:5432
# Local dev: @localhost:5432
export DATABASE_URL="postgresql+asyncpg://microcred:postgres-password@localhost:5432/microcred"
```

## Agent Workflow

1. **Before Writing Code:**
   - Check `docs/architecture/coding-standards.md`
   - Review `docs/architecture/ai-development-guidelines.md`
   - Use `scripts/_template.py` for new scripts

2. **After Writing Code:**
   - Run: `poetry run ruff check --fix .`
   - Run: `poetry run ruff format .`
   - Test imports: `poetry run python -c "from src.api.main import app"`
   - Run: `poetry run pytest tests/`

3. **Before Commit:**
   - Verify all checks pass
   - Ensure no syntax errors
   - Check CI will succeed

## Pre-Commit Checklist (MUST DO)

Before EVERY commit:
1. [ ] `poetry run ruff check .` - no lint errors
2. [ ] `poetry run ruff format --check .` - formatted
3. [ ] `poetry run pytest tests/` - tests pass
4. [ ] No line > 100 characters
5. [ ] No unused imports (F401)
6. [ ] No undefined names (F821)
7. [ ] All dataclass fields provided
8. [ ] Correct model field names
9. [ ] Correct enum values

## Quick References

- Template: `scripts/_template.py`
- Checklist: `docs/PRE-COMMIT-CHECKLIST.md`
- Standards: `docs/architecture/coding-standards.md`
- AI Guide: `docs/architecture/ai-development-guidelines.md`

## Common Fixes

```bash
# Auto-fix linting issues
poetry run ruff check --fix .

# Auto-format code
poetry run ruff format .

# Verify script imports work
poetry run python scripts/your_script.py
```

## Ignored Warnings
- **B008**: FastAPI `Depends()` in function defaults (intentional pattern)

## Questions?
Read: `docs/architecture/ai-development-guidelines.md` for detailed explanations.
