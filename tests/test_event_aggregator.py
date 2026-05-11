"""Tests for the event aggregator service.

Covers two paths:

* The end-to-end pipeline (run_preprocess -> run_full_analysis) against a
  20s synthetic clip rendered by ffmpeg lavfi.
* A direct aggregation test where FrameAnalysis rows are inserted by hand
  to pin the merging behaviour around event_type boundaries.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

# Isolate MEDIA_ROOT and the SQLite database before any project module is
# imported, so we never touch the developer's real ./var directory.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEST_SCRATCH = _REPO_ROOT / "var" / "_pytest_event_aggregator"
_TEST_SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ["MEDIA_ROOT"] = str(_TEST_SCRATCH / "media")
os.environ["DVR_SEMANTIC_DB_URL"] = (
    f"sqlite:///{(_TEST_SCRATCH / 'aggregator.db').as_posix()}"
)
# Force the mock adapter so we don't hit a real model.
os.environ["MODEL_PROVIDER"] = "mock"
os.environ.pop("MODEL_API_KEY", None)

from dvr_semantic_backend.db import (  # noqa: E402 - env vars must be set first
    FrameAnalysis,
    SemanticEvent,
    Video,
    init_db,
    session_scope,
)
from dvr_semantic_backend.services import event_aggregator, media_pipeline  # noqa: E402
from dvr_semantic_backend.services.model_adapter import reset_adapter  # noqa: E402


def _short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


@pytest.fixture(scope="module", autouse=True)
def _prepare_db():
    init_db()
    reset_adapter()
    yield
    # Dispose of the SQLAlchemy engine so Windows releases the SQLite file
    # handle before the directory is removed.
    try:
        from dvr_semantic_backend import db as _db_mod

        _db_mod._engine.dispose()
    except Exception:
        pass
    if _TEST_SCRATCH.exists():
        shutil.rmtree(_TEST_SCRATCH, ignore_errors=True)


def test_run_full_analysis_on_synthetic_clip(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not on PATH")

    src = _TEST_SCRATCH / "_agg_test.mp4"
    if src.exists():
        src.unlink()
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=duration=20:size=320x240:rate=10",
            "-pix_fmt", "yuv420p",
            "-y",
            str(src),
        ],
        check=True,
        capture_output=True,
    )

    video_id = media_pipeline.save_upload(
        file_bytes=src.read_bytes(),
        original_filename="agg.mp4",
        title="aggregator smoke",
        owner_id=None,
    )
    media_pipeline.run_preprocess(video_id, segment_sec=10, frame_interval_sec=3)

    with session_scope() as session:
        pending_frames = (
            session.query(FrameAnalysis)
            .filter(FrameAnalysis.video_id == video_id)
            .count()
        )
    # 20s clip @ one frame per 3s should yield ~7 frames.
    assert pending_frames >= 5

    result = event_aggregator.run_full_analysis(video_id)
    assert result["frames_analyzed"] > 0
    assert result["events_created"] >= 0

    with session_scope() as session:
        video = session.get(Video, video_id)
        assert video is not None
        assert video.process_status == "indexed"

        done_frames = (
            session.query(FrameAnalysis)
            .filter(FrameAnalysis.video_id == video_id)
            .filter(FrameAnalysis.analyze_status == "done")
            .count()
        )
        assert done_frames == result["frames_analyzed"]


def test_aggregate_events_groups_by_type_and_gap() -> None:
    video_id = _short_id("vid")
    with session_scope() as session:
        session.add(
            Video(
                id=video_id,
                title="manual aggregation",
                source_path=str(_TEST_SCRATCH / "synthetic.mp4"),
                duration_sec=60,
                process_status="analyzing",
            )
        )

    # 5 scratch frames at 0/3/6/9/12, then 3 normal, then 2 illegal_parking
    # at 30/33. The "normal" frames sit in the middle but they should not
    # join the scratch group because we skip them, and the time gap to the
    # next scratch group resets the run.
    layout: list[tuple[int, str]] = [
        (0, "scratch"),
        (3, "scratch"),
        (6, "scratch"),
        (9, "scratch"),
        (12, "scratch"),
        (15, "normal"),
        (18, "normal"),
        (21, "normal"),
        (30, "illegal_parking"),
        (33, "illegal_parking"),
    ]

    with session_scope() as session:
        for frame_sec, event_type in layout:
            tag = "剐蹭" if event_type == "scratch" else (
                "违停" if event_type == "illegal_parking" else "正常"
            )
            session.add(
                FrameAnalysis(
                    id=_short_id("frm"),
                    video_id=video_id,
                    frame_sec=frame_sec,
                    frame_path=f"/tmp/{video_id}_{frame_sec}.jpg",
                    tags_json=[tag],
                    frame_summary=f"{event_type} @ {frame_sec}s",
                    vector_text=f"{event_type} {tag}",
                    confidence=0.9,
                    analyze_status="done",
                    model_provider="mock",
                )
            )

    new_event_ids = event_aggregator.aggregate_events(video_id)
    assert len(new_event_ids) == 2

    with session_scope() as session:
        events = (
            session.query(SemanticEvent)
            .filter(SemanticEvent.video_id == video_id)
            .order_by(SemanticEvent.start_sec)
            .all()
        )
        assert [e.event_type for e in events] == ["scratch", "illegal_parking"]

        scratch_evt, parking_evt = events
        assert scratch_evt.start_sec == 0
        assert scratch_evt.end_sec == 12 + 3  # last frame + padding
        assert scratch_evt.title == "疑似剐蹭事件"
        assert "剐蹭" in (scratch_evt.tags_json or [])
        assert scratch_evt.thumbnail_path.endswith("_0.jpg")

        assert parking_evt.start_sec == 30
        assert parking_evt.end_sec == 33 + 3
        assert parking_evt.title == "违停事件"
        assert "违停" in (parking_evt.tags_json or [])

        # Both groups had confidence 0.9 -> review_status='pending'.
        assert scratch_evt.review_status == "pending"
        assert parking_evt.review_status == "pending"

        video = session.get(Video, video_id)
        assert video is not None
        assert video.process_status == "indexed"
