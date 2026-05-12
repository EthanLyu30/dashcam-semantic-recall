"""Smoke tests for the media preprocessing pipeline.

Generates a tiny 3-second test clip with ffmpeg's ``lavfi`` source, runs the
service-layer functions end-to-end against an isolated MEDIA_ROOT + SQLite
database, and asserts that the expected rows / artifacts landed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Point MEDIA_ROOT and the SQLite DB at an isolated location before any
# project module is imported. This keeps the developer's real ``var/`` clean.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEST_SCRATCH = _REPO_ROOT / "var" / "_pytest_media_pipeline"
_TEST_SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ["MEDIA_ROOT"] = str(_TEST_SCRATCH / "media")
os.environ["DVR_SEMANTIC_DB_URL"] = f"sqlite:///{(_TEST_SCRATCH / 'pipeline.db').as_posix()}"

from dvr_semantic_backend.db import (  # noqa: E402  - env vars must be set first
    FrameAnalysis,
    Video,
    VideoSegment,
    init_db,
    session_scope,
)
from dvr_semantic_backend.services import media_pipeline  # noqa: E402


@pytest.fixture(scope="module")
def sample_video_bytes() -> bytes:
    """Generate a 3s synthetic clip with ffmpeg and return its bytes."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not on PATH")
    init_db()
    src = _TEST_SCRATCH / "_test.mp4"
    if src.exists():
        src.unlink()
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=duration=3:size=320x240:rate=10",
        "-pix_fmt", "yuv420p",
        "-y",
        str(src),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    data = src.read_bytes()
    src.unlink()
    return data


def teardown_module(_module):  # noqa: D401 - pytest hook
    """Wipe the scratch directory after the test module finishes."""
    # Dispose of the SQLAlchemy engine so Windows releases the SQLite file
    # handle before we try to delete it.
    try:
        from dvr_semantic_backend import db as _db_mod

        _db_mod._engine.dispose()
    except Exception:
        pass
    if _TEST_SCRATCH.exists():
        shutil.rmtree(_TEST_SCRATCH, ignore_errors=True)


def test_run_preprocess_creates_segments_and_frames(sample_video_bytes: bytes) -> None:
    video_id = media_pipeline.save_upload(
        file_bytes=sample_video_bytes,
        original_filename="smoke.mp4",
        title="smoke test",
        owner_id=None,
    )
    assert video_id.startswith("vid-")

    result = media_pipeline.run_preprocess(
        video_id, segment_sec=1, frame_interval_sec=1
    )

    assert result["segments"] >= 1, result
    assert result["frames"] >= 1, result
    assert result["duration_sec"] >= 1

    # DB rows landed and the video moved to ``analyzing`` (ready for model).
    with session_scope() as session:
        video = session.get(Video, video_id)
        assert video is not None
        assert video.process_status == "analyzing"
        assert video.fail_reason == ""
        assert video.thumbnail_path
        assert Path(video.thumbnail_path).exists()
        assert video.checksum
        assert video.width == 320
        assert video.height == 240

        segments = (
            session.query(VideoSegment)
            .filter(VideoSegment.video_id == video_id)
            .order_by(VideoSegment.segment_index)
            .all()
        )
        assert len(segments) == result["segments"]
        for seg in segments:
            assert Path(seg.file_path).exists()
            assert seg.end_sec > seg.start_sec

        frames = (
            session.query(FrameAnalysis)
            .filter(FrameAnalysis.video_id == video_id)
            .order_by(FrameAnalysis.frame_sec)
            .all()
        )
        assert len(frames) == result["frames"]
        for frm in frames:
            assert frm.analyze_status == "pending"
            assert frm.frame_summary == ""
            assert frm.tags_json == [] or frm.tags_json is None
            assert Path(frm.frame_path).exists()


def test_run_preprocess_marks_failed_for_missing_source() -> None:
    # Create a Video row pointing at a path that doesn't exist on disk.
    init_db()
    import uuid as _uuid

    bogus_id = f"vid-bogus{_uuid.uuid4().hex[:8]}"
    with session_scope() as session:
        session.add(
            Video(
                id=bogus_id,
                title="bogus",
                source_path=str(_TEST_SCRATCH / "nope.mp4"),
                process_status="uploaded",
            )
        )

    with pytest.raises(FileNotFoundError):
        media_pipeline.run_preprocess(bogus_id)

    with session_scope() as session:
        video = session.get(Video, bogus_id)
        assert video is not None
        assert video.process_status == "failed"
        assert "FileNotFoundError" in (video.fail_reason or "")
