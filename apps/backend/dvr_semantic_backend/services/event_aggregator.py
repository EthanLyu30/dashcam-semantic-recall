"""Frame analysis + semantic event aggregation.

Bridges the gap between the media pipeline (which leaves ``FrameAnalysis``
rows in ``pending``) and the search / review layers (which read finished
``SemanticEvent`` rows).

Two stages:

1. :func:`analyze_pending_frames` walks every pending frame for a video,
   asks the configured model adapter for a :class:`FrameLabel`, and writes
   the result back to the ``frame_analysis`` row. Each frame is wrapped in
   its own try/except so a single bad frame can't poison the whole video.

2. :func:`aggregate_events` slides over the analyzed frames in time order,
   merges adjacent same-type frames into a single ``SemanticEvent``, and
   flips the parent ``Video.process_status`` to ``indexed``.

:func:`run_full_analysis` is the convenience wrapper that runs both.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..db import FrameAnalysis, SemanticEvent, Video, session_scope
from .model_adapter import FrameLabel, get_adapter

logger = logging.getLogger(__name__)

# Max gap between two adjacent frames that may still be considered part of
# the same event. Frames are sampled every 3s by default, so 10s leaves
# room for one missed/normal frame in the middle of an event.
_MERGE_GAP_SEC = 10
# Padding added to the last frame's timestamp when computing event end.
_END_PADDING_SEC = 3
# Confidence below this threshold lands the event in the human-review queue.
_REVIEW_THRESHOLD = 0.75

_EVENT_TITLE_MAP: dict[str, str] = {
    "scratch": "疑似剐蹭事件",
    "illegal_parking": "违停事件",
    "road_obstacle": "道路障碍",
    "abnormal_stop": "异常停车/急刹",
    "pedestrian_risk": "行人风险",
}


# ---------------------------------------------------------------------------
# Stage 1: per-frame analysis
# ---------------------------------------------------------------------------


def _build_vector_text(event_type: str, tags: Iterable[str], summary: str) -> str:
    return f"{event_type} {' '.join(tags)} {summary}".strip()


def analyze_pending_frames(video_id: str, max_frames: int | None = None) -> dict:
    """Run the model adapter against every pending frame for ``video_id``.

    Returns a counter dict ``{'total': N, 'done': N, 'failed': N}``. Each
    frame is committed independently so transient failures don't roll back
    the whole batch.
    """
    adapter = get_adapter()

    # Snapshot the pending frame ids + paths first so we don't keep a
    # session open across the model calls.
    with session_scope() as session:
        query = (
            session.query(FrameAnalysis)
            .filter(FrameAnalysis.video_id == video_id)
            .filter(FrameAnalysis.analyze_status == "pending")
            .order_by(FrameAnalysis.frame_sec)
        )
        if max_frames is not None and max_frames > 0:
            query = query.limit(max_frames)
        pending = [(row.id, row.frame_path) for row in query.all()]

    total = len(pending)
    done = 0
    failed = 0

    for frame_id, frame_path in pending:
        path = Path(frame_path)
        try:
            label = adapter.analyze_frame(path, hint="")
            _persist_label(frame_id, label)
            done += 1
        except Exception as exc:  # noqa: BLE001 - we want every frame isolated
            logger.warning(
                "event_aggregator: frame %s analysis failed: %s",
                frame_id,
                exc,
            )
            _persist_failure(frame_id, exc)
            failed += 1

    return {"total": total, "done": done, "failed": failed}


def _persist_label(frame_id: str, label: FrameLabel) -> None:
    tags = list(label.tags)
    vector_text = _build_vector_text(label.event_type, tags, label.summary)
    with session_scope() as session:
        row = session.get(FrameAnalysis, frame_id)
        if row is None:
            return
        row.tags_json = tags
        row.frame_summary = label.summary
        row.confidence = float(label.confidence)
        row.vector_text = vector_text
        row.analyze_status = "done"
        row.model_provider = label.provider


def _persist_failure(frame_id: str, exc: BaseException) -> None:
    try:
        with session_scope() as session:
            row = session.get(FrameAnalysis, frame_id)
            if row is None:
                return
            row.analyze_status = "failed"
            row.frame_summary = f"analyze_failed: {type(exc).__name__}: {exc}"[:500]
    except Exception:  # pragma: no cover - bookkeeping must never escalate
        logger.exception("event_aggregator: failed to record failure for %s", frame_id)


# ---------------------------------------------------------------------------
# Stage 2: aggregation
# ---------------------------------------------------------------------------


def _new_event_id() -> str:
    return f"evt-{uuid.uuid4().hex[:12]}"


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item is None:
            continue
        s = str(item)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def aggregate_events(video_id: str) -> list[str]:
    """Merge analyzed frames into ``SemanticEvent`` rows.

    Returns the ids of newly inserted events. ``Video.process_status`` is
    flipped to ``indexed`` regardless of whether any events were produced
    (the model may have legitimately seen only normal frames).
    """
    with session_scope() as session:
        frames = (
            session.query(FrameAnalysis)
            .filter(FrameAnalysis.video_id == video_id)
            .filter(FrameAnalysis.analyze_status == "done")
            .order_by(FrameAnalysis.frame_sec)
            .all()
        )
        # Materialise to plain dicts so we don't depend on the session after
        # the read closes.
        snapshots = [
            {
                "frame_sec": int(f.frame_sec),
                "frame_path": f.frame_path or "",
                "frame_summary": f.frame_summary or "",
                "tags": list(f.tags_json or []),
                "confidence": float(f.confidence or 0.0),
                "event_type": _infer_event_type(f),
            }
            for f in frames
        ]

    groups = _group_frames(snapshots)
    event_ids: list[str] = []

    with session_scope() as session:
        for group in groups:
            event_id = _new_event_id()
            event = _build_event(video_id, event_id, group)
            session.add(event)
            event_ids.append(event_id)

        video = session.get(Video, video_id)
        if video is not None:
            video.process_status = "indexed"
            video.updated_at = datetime.utcnow()

    return event_ids


def _infer_event_type(frame: FrameAnalysis) -> str:
    """Recover the event_type for a frame.

    The schema doesn't store ``event_type`` directly on ``frame_analysis``
    (the column is shared with the semantic event side). We persist it as
    the first token of ``vector_text`` in :func:`_persist_label`, so we
    can pull it back out here.
    """
    text = frame.vector_text or ""
    first = text.split(" ", 1)[0].strip()
    if first:
        return first
    return "normal"


def _group_frames(frames: list[dict]) -> list[list[dict]]:
    """Bucket adjacent same-type, non-normal frames into events."""
    groups: list[list[dict]] = []
    current: list[dict] = []

    def flush() -> None:
        if current:
            groups.append(current.copy())
            current.clear()

    for frame in frames:
        event_type = frame["event_type"]
        if event_type == "normal" or event_type not in _EVENT_TITLE_MAP:
            flush()
            continue
        if not current:
            current.append(frame)
            continue
        last = current[-1]
        same_type = last["event_type"] == event_type
        close_enough = frame["frame_sec"] - last["frame_sec"] <= _MERGE_GAP_SEC
        if same_type and close_enough:
            current.append(frame)
        else:
            flush()
            current.append(frame)

    flush()
    return groups


def _build_event(video_id: str, event_id: str, group: list[dict]) -> SemanticEvent:
    event_type = group[0]["event_type"]
    title = _EVENT_TITLE_MAP.get(event_type, event_type)

    # Summary: prefer the first frame's. If it's empty, fall back to a
    # join of the first two.
    summary = group[0]["frame_summary"]
    if not summary and len(group) > 1:
        summary = " ".join(
            f["frame_summary"] for f in group[:2] if f["frame_summary"]
        )
    summary = summary or title

    start_sec = group[0]["frame_sec"]
    end_sec = group[-1]["frame_sec"] + _END_PADDING_SEC

    confidences = [f["confidence"] for f in group]
    confidence = sum(confidences) / len(confidences) if confidences else 0.0

    tags_union: list[str] = _dedupe_preserve_order(
        tag for f in group for tag in f["tags"]
    )

    vector_text = f"{title} {summary} {' '.join(tags_union)}".strip()
    review_status = "pending" if confidence >= _REVIEW_THRESHOLD else "reviewing"

    return SemanticEvent(
        id=event_id,
        video_id=video_id,
        event_type=event_type,
        title=title,
        summary=summary,
        start_sec=int(start_sec),
        end_sec=int(end_sec),
        confidence=float(round(confidence, 4)),
        tags_json=tags_union,
        thumbnail_path=group[0]["frame_path"],
        vector_text=vector_text,
        embedding_json=[],
        review_status=review_status,
    )


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------


def run_full_analysis(video_id: str) -> dict:
    """Run :func:`analyze_pending_frames` then :func:`aggregate_events`."""
    counters = analyze_pending_frames(video_id)
    event_ids = aggregate_events(video_id)
    return {
        "frames_analyzed": counters.get("done", 0),
        "events_created": len(event_ids),
    }


__all__ = [
    "analyze_pending_frames",
    "aggregate_events",
    "run_full_analysis",
]
