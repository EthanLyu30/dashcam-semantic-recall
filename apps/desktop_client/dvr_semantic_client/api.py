from __future__ import annotations

import time
from dataclasses import asdict, replace
from typing import Protocol

import requests

from .demo_data import DEMO_EVENTS, DEMO_VIDEOS
from .models import ExportResponse, SearchResponse, SemanticEvent, VideoRecord


class ApiClient(Protocol):
    def list_videos(self) -> tuple[VideoRecord, ...]:
        ...

    def search(self, video_id: str, query: str, mode: str = "hybrid") -> SearchResponse:
        ...

    def get_event(self, event_id: str) -> SemanticEvent:
        ...

    def export_event(self, event_id: str, export_type: str = "package") -> ExportResponse:
        ...


KEYWORD_ALIASES: dict[str, tuple[str, ...]] = {
    "scratch": ("剐蹭", "刮蹭", "碰撞", "擦碰", "scratch"),
    "illegal_parking": ("违停", "停车", "占道", "illegal parking"),
    "road_obstacle": ("障碍", "施工", "围挡", "路障", "obstacle"),
    "abnormal_stop": ("异常停车", "急停", "急刹", "鸣笛", "stop"),
    "pedestrian_risk": ("行人", "横穿", "鬼探头", "pedestrian"),
}


def score_event(query: str, event: SemanticEvent) -> float:
    normalized = query.lower()
    haystack = " ".join(
        [event.event_type, event.title, event.summary, *event.tags]
    ).lower()
    score = 0.0
    for event_type, aliases in KEYWORD_ALIASES.items():
        query_hit = any(alias.lower() in normalized for alias in aliases)
        event_hit = event.event_type == event_type or any(
            alias.lower() in haystack for alias in aliases
        )
        if query_hit and event_hit:
            score += 0.45
    for token in normalized.replace("，", " ").replace(",", " ").split():
        if token and token in haystack:
            score += 0.08
    return min(1.0, score + event.confidence * 0.35)


class MockApiClient:
    def __init__(self) -> None:
        self._events = DEMO_EVENTS
        self._videos = DEMO_VIDEOS

    def list_videos(self) -> tuple[VideoRecord, ...]:
        return self._videos

    def search(self, video_id: str, query: str, mode: str = "hybrid") -> SearchResponse:
        started = time.perf_counter()
        candidates = [event for event in self._events if event.video_id == video_id]
        ranked = sorted(
            ((score_event(query, event), event) for event in candidates),
            key=lambda item: item[0],
            reverse=True,
        )
        results = tuple(event for score, event in ranked if score >= 0.25)
        if not results:
            results = tuple(event for _, event in ranked[:3])
        scored_results = tuple(
            replace(event, similarity_score=score)
            for score, event in ranked
            if event in results
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return SearchResponse(
            query_id=f"mock-{int(started * 1000)}",
            query=query,
            video_id=video_id,
            elapsed_ms=max(12, elapsed_ms),
            results=scored_results,
        )

    def get_event(self, event_id: str) -> SemanticEvent:
        for event in self._events:
            if event.id == event_id:
                return event
        raise KeyError(f"Event not found: {event_id}")

    def export_event(self, event_id: str, export_type: str = "package") -> ExportResponse:
        return ExportResponse(
            event_id=event_id,
            export_id=f"exp-{event_id}",
            status="queued",
            export_path=f"media/exports/{event_id}.{ 'zip' if export_type == 'package' else export_type }",
        )


class RestApiClient:
    def __init__(self, base_url: str, timeout_sec: float = 8.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def list_videos(self) -> tuple[VideoRecord, ...]:
        response = requests.get(f"{self.base_url}/api/videos", timeout=self.timeout_sec)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items", ()) if isinstance(payload, dict) else payload
        return tuple(
            VideoRecord.from_json(item)
            for item in items
            if isinstance(item, dict)
        )

    def search(self, video_id: str, query: str, mode: str = "hybrid") -> SearchResponse:
        response = requests.post(
            f"{self.base_url}/api/search",
            json={"video_id": video_id, "query": query, "mode": mode},
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        return SearchResponse.from_json(response.json())

    def get_event(self, event_id: str) -> SemanticEvent:
        response = requests.get(
            f"{self.base_url}/api/events/{event_id}",
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        return SemanticEvent.from_json(response.json())

    def export_event(self, event_id: str, export_type: str = "package") -> ExportResponse:
        response = requests.post(
            f"{self.base_url}/api/events/{event_id}/export",
            json={
                "export_type": export_type,
                "include_video": True,
                "include_snapshot": True,
                "include_report": True,
            },
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        return ExportResponse.from_json(response.json())


def event_to_json(event: SemanticEvent) -> dict[str, object]:
    data = asdict(event)
    data["tags"] = list(event.tags)
    return data


def video_to_json(video: VideoRecord) -> dict[str, object]:
    return asdict(video)


def create_api_client(base_url: str = "") -> ApiClient:
    if base_url:
        return RestApiClient(base_url)
    return MockApiClient()
