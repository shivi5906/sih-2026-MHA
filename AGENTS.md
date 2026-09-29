# VAULT-X

VAULT-X is an explainable, evidence-driven blockchain tracing and VASP-attribution prototype for lawful investigations.

## Honesty rules

- Label every factual claim as `Observed`, `Inferred`, `Attributed`, or `Uncertain`.
- Abstain rather than guess when evidence is insufficient.
- All scores are **UNCALIBRATED**.
- SAHYOG is **MOCK**; do not imply a live integration.
- Dataset runs must display `SNAPSHOT / CASE REPLAY`.
- Never claim measured accuracy.

## Layout

- `backend/vaultx`: existing tracing engine.
- `backend/app`: new FastAPI application.
- `backend/data/cases/bitfinex2016`: datasets.
- `frontend-revised`: Next.js application.

## Contracts

- API JSON uses camelCase to match `frontend-revised/lib/types.ts`.
- Pydantic v2 models live in `backend/vaultx/schemas`.

## Commands

- Test: `cd backend && pytest -q`
- API: `uvicorn app.main:app --reload --port 8000`
- Web: `cd frontend-revised && pnpm dev`

## Constraints

- No Celery or Redis.
- PostgreSQL and Neo4j are permitted (constraint lifted by user override).
- networkx may still be used for in-memory graph operations.
