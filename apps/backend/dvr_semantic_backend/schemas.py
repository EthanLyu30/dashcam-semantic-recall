from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    video_id: str
    query: str = Field(min_length=1, max_length=500)
    mode: str = "hybrid"


class SearchResponse(BaseModel):
    query: str
    video_id: str
    elapsed_ms: int
    results: list[dict[str, object]]


class ExportRequest(BaseModel):
    export_type: str = "package"
    include_video: bool = True
    include_snapshot: bool = True
    include_report: bool = True


class ExportResponse(BaseModel):
    event_id: str
    export_id: str
    status: str
    export_path: str

