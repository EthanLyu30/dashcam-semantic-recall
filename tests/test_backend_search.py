from __future__ import annotations

from dvr_semantic_backend.demo_store import DEMO_EVENTS
from dvr_semantic_backend.services.search import search_events


def test_backend_search_matches_illegal_parking() -> None:
    results = search_events(DEMO_EVENTS, "vid-20260327-1422", "检索所有违停车辆出现的片段")

    assert results
    assert results[0]["event_type"] == "illegal_parking"


def test_backend_search_is_limited_to_selected_video() -> None:
    results = search_events(DEMO_EVENTS, "vid-20260328-0908", "行人横穿")

    assert results
    assert all(event["video_id"] == "vid-20260328-0908" for event in results)

