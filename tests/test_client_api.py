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
