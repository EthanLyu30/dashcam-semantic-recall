from __future__ import annotations

from dvr_semantic_client.api import MockApiClient
from dvr_semantic_client.models import SemanticEvent, format_time


def test_mock_search_returns_scratch_first_for_scratch_query() -> None:
    client = MockApiClient()
    response = client.search("vid-20260327-1422", "帮我找出疑似剐蹭的时间段")

    assert response.results
    assert response.results[0].event_type == "scratch"
    assert response.results[0].start_sec == 342


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

