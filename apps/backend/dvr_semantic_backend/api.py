from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .demo_store import DEMO_EVENTS, DEMO_VIDEOS, get_event
from .schemas import ExportRequest, ExportResponse, SearchRequest, SearchResponse
from .services.evidence import queue_export
from .services.search import search_events


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dashcam Semantic Recall API",
        version="0.1.0",
        description="Mock API contract for desktop/backend integration.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/videos")
    def list_videos() -> list[dict[str, object]]:
        return DEMO_VIDEOS

    @app.post("/api/search", response_model=SearchResponse)
    def search(request: SearchRequest) -> SearchResponse:
        results = search_events(DEMO_EVENTS, request.video_id, request.query)
        return SearchResponse(
            query=request.query,
            video_id=request.video_id,
            elapsed_ms=24,
            results=results,
        )

    @app.get("/api/events/{event_id}")
    def event_detail(event_id: str) -> dict[str, object]:
        event = get_event(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @app.post("/api/events/{event_id}/export", response_model=ExportResponse)
    def export_event(event_id: str, request: ExportRequest) -> ExportResponse:
        event = get_event(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return queue_export(event_id, request.export_type)

    return app

