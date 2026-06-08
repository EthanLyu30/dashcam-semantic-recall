from __future__ import annotations

import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Protocol

from .demo_data import DEMO_EVENTS, DEMO_VIDEOS
from .models import ExportResponse, SearchResponse, SemanticEvent, VideoRecord


class _RequestsProxy:
    def _module(self) -> Any:
        try:
            import requests
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "REST backend mode requires the 'requests' package. "
                'Install dependencies with: python -m pip install -e ".[desktop,backend]"'
            ) from exc
        return requests

    def get(self, *args: Any, **kwargs: Any) -> Any:
        return self._module().get(*args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> Any:
        return self._module().post(*args, **kwargs)


requests = _RequestsProxy()


class ApiClient(Protocol):
    def list_videos(self) -> tuple[VideoRecord, ...]:
        ...

    def search(self, video_id: str, query: str, mode: str = "hybrid") -> SearchResponse:
        ...

    def get_event(self, event_id: str) -> SemanticEvent:
        ...

    def export_event(self, event_id: str, export_type: str = "package") -> ExportResponse:
        ...

    def dashboard_overview(self) -> dict[str, Any]:
        ...

    def daily_report(self) -> dict[str, Any]:
        ...

    def model_settings(self) -> dict[str, Any]:
        ...

    def list_roles(self) -> dict[str, Any]:
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

    # MockApiClient does not require login; methods kept for API parity.
    def login(self, username: str, password: str) -> dict[str, Any]:
        return {
            "token": "mock-token",
            "user_id": "mock-user",
            "username": username or "demo",
            "role": "admin",
            "display_name": "Mock 演示用户",
        }

    def upload_video(self, file_path: Path, title: str) -> dict[str, Any]:
        return {
            "video_id": f"mock-{int(time.time())}",
            "status": "uploaded",
            "request_id": "mock",
        }

    def process_video(self, video_id: str) -> dict[str, Any]:
        return {
            "video_id": video_id,
            "frames_analyzed": 0,
            "events_created": 0,
            "status": "analyzed",
        }

    def dashboard_overview(self) -> dict[str, Any]:
        return {
            "processed_video_count": len(self._videos),
            "semantic_query_count": 0,
            "identified_event_count": len(self._events),
            "pending_review_count": sum(
                1 for event in self._events if event.review_status in {"pending", "reviewing"}
            ),
            "engine_status": "demo",
            "model_nodes": {
                "online": 1,
                "total": 1,
                "provider": "mock",
                "api_key_configured": False,
            },
        }

    def daily_report(self) -> dict[str, Any]:
        return {
            "date": "2026-03-27",
            "processed_video_count": len(self._videos),
            "identified_event_count": len(self._events),
            "semantic_query_count": 0,
            "evidence_export_count": 0,
            "pending_review_count": 0,
            "event_distribution": [],
            "risk_summary": "Mock 演示数据已加载，可离线展示检索与回放流程。",
        }

    def model_settings(self) -> dict[str, Any]:
        return {
            "provider": "mock",
            "model_name": "MockAdapter",
            "base_url": "",
            "api_key_configured": False,
            "use_embeddings": False,
            "media_root": "./var/media",
            "db_engine": "memory-demo",
        }

    def list_roles(self) -> dict[str, Any]:
        return {
            "items": [
                {"id": "admin", "name": "管理员", "permissions": ["*"]},
                {"id": "reviewer", "name": "审核人员", "permissions": ["event:review"]},
                {"id": "user", "name": "普通用户", "permissions": ["search:create"]},
            ]
        }


class RestApiClient:
    def __init__(self, base_url: str, timeout_sec: float = 8.0, token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.token = token

    # --- helpers -----------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _get(self, path: str) -> requests.Response:
        kwargs: dict[str, Any] = {"timeout": self.timeout_sec}
        if self.token:
            kwargs["headers"] = self._headers()
        return requests.get(f"{self.base_url}{path}", **kwargs)

    def _get_json(self, path: str) -> dict[str, Any]:
        response = self._get(path)
        response.raise_for_status()
        payload = response.json() or {}
        if isinstance(payload, dict):
            return payload
        return {"items": payload}

    def _post_json(self, path: str, payload: dict[str, Any]) -> requests.Response:
        kwargs: dict[str, Any] = {"timeout": self.timeout_sec, "json": payload}
        if self.token:
            kwargs["headers"] = self._headers()
        return requests.post(f"{self.base_url}{path}", **kwargs)

    def _post_json_response(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._post_json(path, payload or {})
        response.raise_for_status()
        data = response.json() or {}
        if isinstance(data, dict):
            return data
        return {"items": data}

    # --- auth --------------------------------------------------------------
    def login(self, username: str, password: str) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        payload = response.json() or {}
        token = str(payload.get("token", ""))
        if token:
            self.token = token
        return payload

    # --- videos ------------------------------------------------------------
    def list_videos(self) -> tuple[VideoRecord, ...]:
        payload = self._get_json("/api/videos")
        items = payload.get("items", ()) if isinstance(payload, dict) else payload
        return tuple(
            VideoRecord.from_json(item)
            for item in items
            if isinstance(item, dict)
        )

    def upload_video(self, file_path: Path, title: str) -> dict[str, Any]:
        path = Path(file_path)
        with path.open("rb") as fh:
            files = {"file": (path.name, fh, "application/octet-stream")}
            data = {"title": title}
            kwargs: dict[str, Any] = {
                "timeout": max(self.timeout_sec, 60.0),
                "files": files,
                "data": data,
            }
            if self.token:
                kwargs["headers"] = self._headers()
            response = requests.post(
                f"{self.base_url}/api/videos/upload", **kwargs
            )
        response.raise_for_status()
        return response.json() or {}

    def process_video(self, video_id: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"timeout": max(self.timeout_sec, 120.0)}
        if self.token:
            kwargs["headers"] = self._headers()
        response = requests.post(
            f"{self.base_url}/api/videos/{video_id}/process", **kwargs
        )
        response.raise_for_status()
        return response.json() or {}

    def stream_url(self, video_id: str) -> str:
        return f"{self.base_url}/api/videos/{video_id}/stream"

    # --- search & events ---------------------------------------------------
    def search(
        self,
        video_id: str,
        query: str,
        mode: str = "hybrid",
        top_k: int = 10,
    ) -> SearchResponse:
        payload = {
            "video_id": video_id or None,
            "query": query,
            "mode": mode,
            "top_k": top_k,
        }
        response = self._post_json("/api/search", payload)
        response.raise_for_status()
        return SearchResponse.from_json(response.json())

    def get_event(self, event_id: str) -> SemanticEvent:
        response = self._get(f"/api/events/{event_id}")
        response.raise_for_status()
        return SemanticEvent.from_json(response.json())

    def export_event(self, event_id: str, export_type: str = "package") -> ExportResponse:
        payload = {
            "export_type": export_type,
            "include_video": True,
            "include_snapshot": True,
            "include_report": True,
        }
        response = self._post_json(f"/api/events/{event_id}/export", payload)
        response.raise_for_status()
        return ExportResponse.from_json(response.json())

    def export_batch(
        self,
        event_ids: list[str],
        include_video: bool = True,
        include_snapshot: bool = True,
        include_report: bool = True,
        force: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "event_ids": list(event_ids),
            "include_video": include_video,
            "include_snapshot": include_snapshot,
            "include_report": include_report,
            "force": force,
        }
        return self._post_json_response("/api/exports/batch", payload)

    # --- final-stage operational APIs -------------------------------------
    def dashboard_overview(self) -> dict[str, Any]:
        return self._get_json("/api/dashboard/overview")

    def dashboard_trends(self, days: int = 7) -> dict[str, Any]:
        return self._get_json(f"/api/dashboard/trends?days={int(days)}")

    def event_distribution(self) -> dict[str, Any]:
        return self._get_json("/api/dashboard/event-distribution")

    def review_feed(self, limit: int = 20) -> dict[str, Any]:
        return self._get_json(f"/api/dashboard/review-feed?limit={int(limit)}")

    def alerts_summary(self) -> dict[str, Any]:
        return self._get_json("/api/alerts/summary")

    def list_alerts(self) -> dict[str, Any]:
        return self._get_json("/api/alerts")

    def list_accidents(self) -> dict[str, Any]:
        return self._get_json("/api/accidents")

    def list_exports(self) -> dict[str, Any]:
        return self._get_json("/api/exports")

    def daily_report(self) -> dict[str, Any]:
        return self._get_json("/api/reports/daily")

    def export_daily_report(self) -> dict[str, Any]:
        return self._post_json_response("/api/reports/daily/export")

    def model_settings(self) -> dict[str, Any]:
        return self._get_json("/api/settings/model")

    def model_test(self) -> dict[str, Any]:
        return self._post_json_response("/api/settings/model/test")

    def security_settings(self) -> dict[str, Any]:
        return self._get_json("/api/settings/security")

    def list_users(self) -> dict[str, Any]:
        return self._get_json("/api/users")

    def list_roles(self) -> dict[str, Any]:
        return self._get_json("/api/roles")

    def list_permissions(self) -> dict[str, Any]:
        return self._get_json("/api/permissions")


def event_to_json(event: SemanticEvent) -> dict[str, object]:
    data = asdict(event)
    data["tags"] = list(event.tags)
    return data


def video_to_json(video: VideoRecord) -> dict[str, object]:
    return asdict(video)


def create_api_client(base_url: str = "", token: str = "") -> ApiClient:
    if base_url:
        return RestApiClient(base_url, token=token)
    return MockApiClient()
