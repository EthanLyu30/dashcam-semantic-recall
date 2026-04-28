# Dashcam Semantic Recall - Agent Guide

This file is the canonical guide for coding agents and developers working in this repository.

## Product Goal

Build a desktop-first AI application for long dashcam videos:

1. Upload and preprocess video.
2. Generate semantic events with timestamps.
3. Search events with natural language.
4. Click a result and seek to the exact playback segment.
5. Export evidence and logs.

## Project Structure

```text
dashcam-semantic-recall/
├── apps/
│   ├── desktop_client/          # 吕霄阳: Qt6 desktop client and demo flow
│   │   └── dvr_semantic_client/
│   │       ├── widgets/         # Player, search, result cards, timeline
│   │       └── resources/       # QSS theme
│   └── backend/                 # 倪羽辰: FastAPI, video, AI, DB, evidence APIs
│       └── dvr_semantic_backend/
│           └── services/        # Pure backend services that are easy to test
├── docs/                        # API contract, handoff, requirement trace
├── plans/                       # Implementation roadmap
├── skills/                      # Project-specific procedural skills
└── tests/                       # Focused tests for completed behavior
```

## Ownership Boundary

吕霄阳 can freely edit:

- `apps/desktop_client/**`
- `docs/api-contract.md`
- `docs/team-handoff.md`
- `docs/prototype-source/**`
- `docs/prototype-migration.md`
- `docs/lv-xiaoyang-completed.md`
- `DESIGN.md`

倪羽辰 can freely edit:

- `apps/backend/**`
- database migrations when added
- video/AI/search/evidence services
- backend tests and technical implementation docs
- `docs/ni-yuchen-todolist.md`

Shared files such as `README.md`, `AGENTS.md`, `pyproject.toml`, and API contracts should be updated deliberately because they affect both members.

## Development Pattern

Follow a Hermes-style layout:

- Keep stable entry points obvious: `apps/desktop_client/main.py`, `apps/backend/main.py`.
- Put repeatable procedures in `skills/*/SKILL.md`.
- Put non-trivial execution plans in `plans/`.
- Keep pure business logic in service modules so it can be tested without UI or server startup.
- Treat `.env` as secret-only. Non-secret defaults belong in code or config files.

Follow the Karpathy-inspired rules from `开发技巧.md`:

- State assumptions for ambiguous implementation work.
- Prefer the minimum code that satisfies the current requirement.
- Avoid speculative abstractions and unrelated refactors.
- Define success criteria and verify them.

## Prototype Migration Rule

The UI is not allowed to drift away from the completed DVR-Semantic prototype. Use `docs/prototype-migration.md` as the migration checklist and keep `docs/prototype-source/` as the visual/source reference. The final client should be reproduced in the required Qt6 desktop stack; the HTML prototype is a design reference, not the final implementation.

## Current Success Criteria

The scaffold is considered ready for handoff when:

- `python -m compileall apps tests` succeeds.
- `python -m pytest` succeeds for the pure contract/search tests.
- The desktop client can run with mock data after installing `desktop` dependencies.
- Backend TODOs for 倪羽辰 are visible and mapped to API contracts.
