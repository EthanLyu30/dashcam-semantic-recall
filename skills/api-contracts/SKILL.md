---
name: api-contracts
description: Use when changing REST request/response fields shared by the Qt client and FastAPI backend.
owner: shared
---

# API Contracts Skill

## Rule

The client and backend must communicate through stable DTOs documented in `docs/api-contract.md`.

## Required Flow

1. Update the documentation first.
2. Update `apps/desktop_client/dvr_semantic_client/models.py`.
3. Update backend schemas/endpoints.
4. Update tests with one representative JSON object.

## Guardrails

- Timestamps are seconds on the original video timeline.
- `confidence` is a float from 0 to 1.
- `review_status` values should remain: `pending`, `confirmed`, `rejected`, `reviewing`.

