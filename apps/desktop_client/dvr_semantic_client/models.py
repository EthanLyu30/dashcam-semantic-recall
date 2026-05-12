from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def format_time(seconds: int) -> str:
    minutes, sec = divmod(max(0, int(seconds)), 60)
    hour, minute = divmod(minutes, 60)
    if hour:
        return f"{hour:02d}:{minute:02d}:{sec:02d}"
    return f"{minute:02d}:{sec:02d}"


@dataclass(frozen=True)
class VideoRecord:
    id: str
    title: str
    duration_sec: int
    status: str = "searchable"
    thumbnail_url: str = ""
    source_path: str = ""
    fail_reason: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "VideoRecord":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "Untitled video")),
            duration_sec=int(data.get("duration_sec", 0)),
            status=str(data.get("status", "unknown")),
            thumbnail_url=str(data.get("thumbnail_url", "")),
            source_path=str(data.get("source_path", "")),
            fail_reason=str(data.get("fail_reason", "")),
        )


@dataclass(frozen=True)
class SemanticEvent:
    id: str
    video_id: str
    event_type: str
    title: str
    summary: str
    start_sec: int
    end_sec: int
    confidence: float
    tags: tuple[str, ...] = field(default_factory=tuple)
    thumbnail_url: str = ""
    review_status: str = "pending"
    similarity_score: float = 0.0
    rank_no: int = 0
    answer_text: str = ""

    @property
    def time_range(self) -> str:
        return f"{format_time(self.start_sec)} - {format_time(self.end_sec)}"

    @property
    def confidence_percent(self) -> str:
        return f"{round(self.confidence * 100):d}%"

    @property
    def similarity_percent(self) -> str:
        return f"{round(self.similarity_score * 100):d}%"

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "SemanticEvent":
        tags = data.get("tags", ())
        if isinstance(tags, str):
            tags = [tags]
        return cls(
            id=str(data.get("id", "")),
            video_id=str(data.get("video_id", "")),
            event_type=str(data.get("event_type", "unknown")),
            title=str(data.get("title", "Untitled event")),
            summary=str(data.get("summary", "")),
            start_sec=int(data.get("start_sec", 0)),
            end_sec=int(data.get("end_sec", 0)),
            confidence=float(data.get("confidence", 0.0)),
            tags=tuple(str(tag) for tag in tags),
            thumbnail_url=str(data.get("thumbnail_url", "")),
            review_status=str(data.get("review_status", "pending")),
            similarity_score=float(data.get("similarity_score", 0.0)),
            rank_no=int(data.get("rank_no", 0)),
            answer_text=str(data.get("answer_text", "")),
        )


@dataclass(frozen=True)
class SearchResponse:
    query_id: str
    query: str
    video_id: str
    elapsed_ms: int
    results: tuple[SemanticEvent, ...]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "SearchResponse":
        return cls(
            query_id=str(data.get("query_id", "")),
            query=str(data.get("query", "")),
            video_id=str(data.get("video_id", "")),
            elapsed_ms=int(data.get("elapsed_ms", 0)),
            results=tuple(
                SemanticEvent.from_json(item)
                for item in data.get("results", [])
                if isinstance(item, dict)
            ),
        )


@dataclass(frozen=True)
class ExportResponse:
    event_id: str
    export_id: str
    status: str
    export_path: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ExportResponse":
        return cls(
            event_id=str(data.get("event_id", "")),
            export_id=str(data.get("export_id", "")),
            status=str(data.get("status", "queued")),
            export_path=str(data.get("export_path", "")),
        )
