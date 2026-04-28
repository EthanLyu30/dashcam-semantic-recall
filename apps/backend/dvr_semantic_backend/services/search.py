from __future__ import annotations

from typing import Iterable


KEYWORD_ALIASES: dict[str, tuple[str, ...]] = {
    "scratch": ("剐蹭", "刮蹭", "碰撞", "擦碰", "scratch"),
    "illegal_parking": ("违停", "停车", "占道", "illegal parking"),
    "road_obstacle": ("障碍", "施工", "围挡", "路障", "obstacle"),
    "abnormal_stop": ("异常停车", "急停", "急刹", "鸣笛", "stop"),
    "pedestrian_risk": ("行人", "横穿", "鬼探头", "pedestrian"),
}


def score_event(query: str, event: dict[str, object]) -> float:
    normalized = query.lower()
    tags = event.get("tags", [])
    tags_text = " ".join(str(tag) for tag in tags) if isinstance(tags, list) else str(tags)
    haystack = " ".join(
        [
            str(event.get("event_type", "")),
            str(event.get("title", "")),
            str(event.get("summary", "")),
            tags_text,
        ]
    ).lower()
    score = 0.0
    for event_type, aliases in KEYWORD_ALIASES.items():
        query_hit = any(alias.lower() in normalized for alias in aliases)
        event_hit = event.get("event_type") == event_type or any(
            alias.lower() in haystack for alias in aliases
        )
        if query_hit and event_hit:
            score += 0.45
    for token in normalized.replace("，", " ").replace(",", " ").split():
        if token and token in haystack:
            score += 0.08
    confidence = float(event.get("confidence", 0.0))
    return min(1.0, score + confidence * 0.35)


def search_events(
    events: Iterable[dict[str, object]], video_id: str, query: str
) -> list[dict[str, object]]:
    candidates = [event for event in events if event.get("video_id") == video_id]
    ranked = sorted(
        ((score_event(query, event), event) for event in candidates),
        key=lambda item: item[0],
        reverse=True,
    )
    results = [event for score, event in ranked if score >= 0.25]
    if not results:
        results = [event for _, event in ranked[:3]]
    return results

