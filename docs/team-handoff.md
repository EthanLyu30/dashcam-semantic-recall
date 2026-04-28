# Team Handoff

## Source Basis

This scaffold is based on the completed requirements document, outline design document, first-stage report, opening report, and DVR-Semantic interaction prototype in the parent workspace.

## 吕霄阳 Completed Scope

The current repository implements the client-side contribution first:

- Complete DVR-Semantic prototype assets copied into `docs/prototype-source/` as UI design reference.
- No-dependency prototype reference viewer: `python apps/desktop_client/run_prototype.py`.
- Qt WebEngine prototype reference shell: `python apps/desktop_client/prototype_shell.py`.
- Qt6 native multi-page reproduction for the prototype navigation and major pages.
- Qt6 semantic-search page: playback, query, result list, event detail, and timeline.
- Mock API client with deterministic videos/events/search results.
- Result selection to playback seek flow.
- Event export trigger against the shared API contract.
- Design system, prototype migration guide, and API/data models.

The full prototype can run without desktop dependencies through the prototype runner. The Qt scaffold can run against mock data after installing `desktop` dependencies, and can call a real REST server when `DVR_SEMANTIC_API_BASE` is set.

## 倪羽辰 Remaining Scope

Backend and AI implementation should fill the contracts without changing the client DTOs unless a contract change is agreed.

Required core tasks:

1. Implement video upload and task creation.
2. Use ffmpeg for metadata extraction, transcoding, slicing, keyframe extraction, thumbnails, and clip export.
3. Implement multimodal model adapter with structured JSON output.
4. Persist videos, segments, frame analysis, semantic events, queries, results, exports, users, roles, and logs.
5. Implement hybrid semantic retrieval with pgvector plus keyword fallback.
6. Implement evidence export package generation and audit records.
7. Add backend integration tests and endpoint tests.

Dashboard, report, alert, settings, user, and role pages may stay on mock data during the first backend milestone. They are not blockers for 倪羽辰's first delivery.

## Integration Contract

The client only requires:

- `video_id`
- `event_id`
- `start_sec`
- `end_sec`
- `title`
- `summary`
- `event_type`
- `confidence`
- optional `thumbnail_url`

As long as those fields remain stable, backend internals can evolve independently.
