# AGENTS.md — openai-reasoning-budget-futures

**Company:** OpenAI
**Domain:** ML Inference Optimization & KV-Cache Management

## Quick Rules
- **Test command:** `PYTHONPATH=src pytest tests/ -v`
- **Lint:** `ruff check src/ tests/`
- **No drive-by edits** — load the skill first.

## Architecture
- `src/openai_reasoning_budget_futures/core.py` — Domain logic (ML Inference Optimization & KV-Cache Management)
- `tests/` — Verified test suite
- `.github/workflows/ci.yml` — Enforced CI pipeline
