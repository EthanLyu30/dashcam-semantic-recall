---
name: semantic-search
description: Use when implementing query understanding, hybrid retrieval, event ranking, or pgvector integration.
owner: 倪羽辰
---

# Semantic Search Skill

## Goal

Turn a natural-language query into ranked semantic events with clear timestamps and explanations.

## Recommended Pipeline

1. Normalize query and extract keywords.
2. Embed query text.
3. Run pgvector recall over frame/event semantic text.
4. Run keyword fallback over event type, tags, and summaries.
5. Rerank by semantic score, keyword hit, confidence, and event completeness.
6. Persist query and result records.

## Minimal Demo Fallback

If pgvector is not available, use keyword scoring in `dvr_semantic_backend/services/search.py` until the database layer is ready.

