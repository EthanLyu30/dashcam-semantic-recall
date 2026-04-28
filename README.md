# Dashcam Semantic Recall

English project name: `dashcam-semantic-recall`

Dashcam Semantic Recall is a course project scaffold for a multimodal AI system that turns long dashcam videos into searchable semantic events, then lets users jump to the exact playback segment and export evidence.

The project is derived from the completed SRS, outline design document, first-stage report, opening report, and DVR-Semantic interaction prototype in the parent workspace.

## Scope

This repository is intentionally split by the two-person team boundary from the opening report.

吕霄阳 owns the desktop client and presentation layer:

- Qt6 desktop workspace and page layout
- VLC-compatible playback panel and timestamp seek flow
- Semantic search results, event detail, and event timeline interaction
- REST contract integration and final demo flow

倪羽辰 owns the backend and AI implementation:

- Video upload, transcoding, slicing, frame extraction
- Multimodal model API integration and structured labels
- Semantic retrieval, event summaries, timestamp return logic
- Database, logs, evidence export implementation, tests, and technical docs

## What Is Implemented Now

- A runnable PySide6 Qt6 desktop client scaffold under `apps/desktop_client`
- Mock API client and deterministic demo data so the UI can be demonstrated before the backend is complete
- A backend placeholder with FastAPI endpoint contracts and pure search-service logic
- `AGENTS.md`, `开发技巧.md`, `DESIGN.md`, project skills, roadmap, and handoff docs
- Unit tests for the completed contract/search logic

Important design note: the desktop client must migrate the completed DVR-Semantic prototype rather than inventing a new UI. The source prototype is copied under `docs/prototype-source/`, and the page/API mapping is documented in `docs/prototype-migration.md`.

## Quick Start

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e ".[dev,desktop,backend]"
```

Run the desktop demo:

```bash
python apps/desktop_client/main.py
```

Run the mock backend:

```bash
uvicorn apps.backend.main:app --reload --port 8000
```

Point the desktop client at the backend:

```bash
$env:DVR_SEMANTIC_API_BASE="http://127.0.0.1:8000"
python apps/desktop_client/main.py
```

Run tests:

```bash
python -m pytest
```

## Reference Style

The scaffold borrows the following ideas from the requested references:

- Hermes Agent: explicit project guide, skills, tools/services, plans, and stable contracts.
- Karpathy guidelines: minimal scope, surgical changes, success criteria, and verification loops.
- DESIGN.md pattern: a root design-system document that coding agents can follow consistently.
