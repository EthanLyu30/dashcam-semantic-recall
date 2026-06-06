# Phase 2 Roadmap

## Milestone A - Client Demo Ready

Owner: 吕霄阳

- Qt6 workspace opens with mock data.
- Suggested queries return event cards.
- Clicking an event seeks the playback panel to `start_sec`.
- Timeline highlights the selected event.
- Evidence export action calls the API contract or mock fallback.

Verification:

- `python -m compileall apps tests`
- `python -m pytest`
- Manual run: `python apps/desktop_client/main.py`

## Milestone B - Backend Contract Ready

Owner: 倪羽辰

- FastAPI endpoint responses match `docs/api-contract.md`.
- Upload creates video/task records.
- Search returns stable event DTOs.
- Export returns queued/exported status.

Verification:

- API endpoint tests.
- Client can run with `DVR_SEMANTIC_API_BASE=http://127.0.0.1:8000`.

## Milestone C - AI And Video Pipeline

Owner: 倪羽辰

- ffmpeg metadata, slicing, frames, thumbnails.
- Multimodal model adapter.
- Structured event extraction.
- PostgreSQL `REAL[]` vector search with SQLite fallback.
- Evidence package export.

Verification:

- Sample 2-hour video processing.
- Three demo queries: scratch, illegal parking, abnormal stop.
- Playback seek accuracy within 2 seconds.
