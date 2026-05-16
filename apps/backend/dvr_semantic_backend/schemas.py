from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: str
    username: str
    role: str
    display_name: str = ""


class VideoOut(BaseModel):
    id: str
    title: str
    duration_sec: int
    status: str
    thumbnail_url: str = ""
    source_path: str = ""
    fail_reason: str = ""


class VideoListResponse(BaseModel):
    items: list[VideoOut]


class UploadResponse(BaseModel):
    video_id: str
    status: str
    request_id: str


class ProcessReport(BaseModel):
    video_id: str
    segments: int
    frames: int
    duration_sec: int
    status: str


class AnalysisReport(BaseModel):
    video_id: str
    frames_analyzed: int
    events_created: int
    status: str


class EventOut(BaseModel):
    id: str
    video_id: str
    event_type: str
    title: str
    summary: str
    start_sec: int
    end_sec: int
    confidence: float
    tags: list[str]
    thumbnail_url: str = ""
    review_status: str = "pending"
    similarity_score: float = 0.0
    rank_no: int = 0
    answer_text: str = ""


class SearchRequest(BaseModel):
    video_id: str | None = None
    query: str = Field(min_length=1, max_length=500)
    mode: str = "hybrid"
    top_k: int = 10


class SearchResponse(BaseModel):
    query_id: str
    query: str
    video_id: str | None
    mode: str
    elapsed_ms: int
    results: list[EventOut]


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


class ReviewRequest(BaseModel):
    """Legacy review endpoint (deprecated in favour of ReviewDecisionRequest)."""
    review_status: str
    note: str = ""


class ReviewDecisionRequest(BaseModel):
    """POST /api/review/tasks/{event_id}/decision"""
    decision: str  # "confirmed" | "rejected" | "pending"
    corrected_event_type: str | None = None
    corrected_title: str | None = None
    corrected_tags: list[str] = []
    note: str = ""


class ReviewTaskItem(BaseModel):
    event_id: str
    video_id: str
    event_type: str
    title: str
    confidence: float
    review_status: str
    thumbnail_url: str = ""
    created_at: str = ""


class ReviewTaskListResponse(BaseModel):
    items: list[ReviewTaskItem]
    total: int


class ReviewDecisionResponse(BaseModel):
    event_id: str
    review_status: str
    reviewer_id: str
    reviewed_at: str


class AuditLogOut(BaseModel):
    id: str
    request_id: str
    user_id: str | None = None
    action: str
    target_type: str = ""
    target_id: str = ""
    result_code: str = "00000"
    message: str = ""
    created_at: str


class EnvelopeError(BaseModel):
    request_id: str
    code: str
    message: str
    data: dict[str, Any] | None = None
