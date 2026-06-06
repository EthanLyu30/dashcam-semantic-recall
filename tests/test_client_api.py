from __future__ import annotations

from dvr_semantic_client.api import MockApiClient, RestApiClient
from dvr_semantic_client.models import SemanticEvent, format_time


def test_mock_search_returns_scratch_first_for_scratch_query() -> None:
    client = MockApiClient()
    response = client.search("vid-20260327-1422", "帮我找出疑似剐蹭的时间段")

    assert response.results
    assert response.results[0].event_type == "scratch"
    assert response.results[0].start_sec == 342
    assert response.results[0].similarity_score > 0.7
    assert response.query_id.startswith("mock-")


def test_mock_search_returns_pedestrian_first_for_pedestrian_query() -> None:
    client = MockApiClient()
    response = client.search("vid-20260328-0908", "找出行人横穿导致急刹的片段")

    assert response.results
    assert response.results[0].event_type == "pedestrian_risk"
    assert response.results[0].similarity_score > response.results[-1].similarity_score


def test_event_model_formats_time_range() -> None:
    event = SemanticEvent(
        id="e1",
        video_id="v1",
        event_type="scratch",
        title="test",
        summary="summary",
        start_sec=61,
        end_sec=125,
        confidence=0.9,
    )

    assert format_time(61) == "01:01"
    assert event.time_range == "01:01 - 02:05"


def test_rest_client_accepts_paginated_video_contract(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "items": [
                    {
                        "id": "vid-1",
                        "title": "demo",
                        "duration_sec": 120,
                        "status": "searchable",
                    }
                ],
                "page": 1,
                "page_size": 20,
                "total": 1,
            }

    def fake_get(url: str, timeout: float) -> Response:
        assert url == "http://example.test/api/videos"
        assert timeout == 8.0
        return Response()

    monkeypatch.setattr("dvr_semantic_client.api.requests.get", fake_get)

    videos = RestApiClient("http://example.test").list_videos()

    assert len(videos) == 1
    assert videos[0].id == "vid-1"


def test_mock_client_exposes_final_stage_snapshots() -> None:
    client = MockApiClient()

    overview = client.dashboard_overview()
    report = client.daily_report()
    settings = client.model_settings()
    roles = client.list_roles()

    assert overview["engine_status"] == "demo"
    assert overview["identified_event_count"] > 0
    assert report["risk_summary"]
    assert settings["provider"] == "mock"
    assert {item["id"] for item in roles["items"]} == {"admin", "reviewer", "user"}


def test_rest_client_final_stage_methods_call_expected_paths(monkeypatch) -> None:
    seen: list[tuple[str, str]] = []

    class Response:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    get_payloads = {
        "/api/dashboard/overview": {"engine_status": "healthy"},
        "/api/dashboard/trends?days=3": {"days": ["06-06"]},
        "/api/dashboard/event-distribution": {"items": []},
        "/api/dashboard/review-feed?limit=2": {"items": []},
        "/api/alerts/summary": {"open_count": 0},
        "/api/alerts": {"items": [], "total": 0},
        "/api/accidents": {"items": []},
        "/api/exports": {"items": []},
        "/api/reports/daily": {"date": "2026-06-06"},
        "/api/settings/model": {"provider": "deepseek"},
        "/api/settings/security": {"bearer_auth_enabled": True},
        "/api/users": {"items": []},
        "/api/roles": {"items": []},
        "/api/permissions": {"permissions": []},
    }
    post_payloads = {
        "/api/reports/daily/export": {"status": "success"},
        "/api/settings/model/test": {"status": "configured"},
    }

    def fake_get(url: str, timeout: float, headers=None) -> Response:
        path = url.removeprefix("http://example.test")
        seen.append(("GET", path))
        return Response(get_payloads[path])

    def fake_post(url: str, timeout: float, json=None, headers=None) -> Response:
        path = url.removeprefix("http://example.test")
        seen.append(("POST", path))
        return Response(post_payloads[path])

    monkeypatch.setattr("dvr_semantic_client.api.requests.get", fake_get)
    monkeypatch.setattr("dvr_semantic_client.api.requests.post", fake_post)

    client = RestApiClient("http://example.test", token="tok")

    assert client.dashboard_overview()["engine_status"] == "healthy"
    assert client.dashboard_trends(days=3)["days"] == ["06-06"]
    assert client.event_distribution()["items"] == []
    assert client.review_feed(limit=2)["items"] == []
    assert client.alerts_summary()["open_count"] == 0
    assert client.list_alerts()["total"] == 0
    assert client.list_accidents()["items"] == []
    assert client.list_exports()["items"] == []
    assert client.daily_report()["date"] == "2026-06-06"
    assert client.export_daily_report()["status"] == "success"
    assert client.model_settings()["provider"] == "deepseek"
    assert client.model_test()["status"] == "configured"
    assert client.security_settings()["bearer_auth_enabled"] is True
    assert client.list_users()["items"] == []
    assert client.list_roles()["items"] == []
    assert client.list_permissions()["permissions"] == []

    assert ("GET", "/api/dashboard/overview") in seen
    assert ("POST", "/api/settings/model/test") in seen
