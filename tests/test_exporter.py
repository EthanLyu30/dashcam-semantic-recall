"""Smoke tests for the evidence exporter service.

Generates a 15s synthetic test clip, registers it via media_pipeline, attaches
a SemanticEvent, then runs the full export_package() pipeline against an
isolated MEDIA_ROOT + SQLite database. Verifies that the package.zip is
produced with the expected member files and that an EventExport row tracks
the result.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

import pytest

# Isolate MEDIA_ROOT and the SQLite DB before importing project modules.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEST_SCRATCH = _REPO_ROOT / "var" / "_pytest_exporter"
_TEST_SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ["MEDIA_ROOT"] = str(_TEST_SCRATCH / "media")
os.environ["DVR_SEMANTIC_DB_URL"] = f"sqlite:///{(_TEST_SCRATCH / 'exporter.db').as_posix()}"

from dvr_semantic_backend.db import (  # noqa: E402
    EventExport,
    SemanticEvent,
    Video,
    init_db,
    session_scope,
)
from dvr_semantic_backend.services import exporter, media_pipeline  # noqa: E402


@pytest.fixture(scope="module")
def sample_video_bytes() -> bytes:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not on PATH")
    init_db()
    src = _TEST_SCRATCH / "_test15.mp4"
    if src.exists():
        src.unlink()
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=duration=15:size=320x240:rate=10",
        "-pix_fmt", "yuv420p",
        "-y",
        str(src),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    data = src.read_bytes()
    src.unlink()
    return data


def teardown_module(_module):  # noqa: D401
    try:
        from dvr_semantic_backend import db as _db_mod
        _db_mod._engine.dispose()
    except Exception:
        pass
    if _TEST_SCRATCH.exists():
        shutil.rmtree(_TEST_SCRATCH, ignore_errors=True)


def _make_event(video_id: str, start_sec: int = 3, end_sec: int = 8) -> str:
    event_id = f"evt-{uuid.uuid4().hex[:10]}"
    with session_scope() as session:
        session.add(
            SemanticEvent(
                id=event_id,
                video_id=video_id,
                event_type="incident",
                title="测试事件",
                summary="行车记录仪检测到的测试事件，用于导出流水线烟雾测试。",
                start_sec=start_sec,
                end_sec=end_sec,
                confidence=0.87,
                tags_json=["pedestrian", "brake"],
                thumbnail_path="",
                vector_text="测试事件",
                embedding=[],
                review_status="confirmed",
            )
        )
    return event_id


def test_export_package_end_to_end(sample_video_bytes: bytes) -> None:
    video_id = media_pipeline.save_upload(
        file_bytes=sample_video_bytes,
        original_filename="exporter.mp4",
        title="exporter smoke",
        owner_id=None,
    )
    meta = media_pipeline.probe_metadata(video_id)
    assert meta["duration_sec"] >= 10

    event_id = _make_event(video_id, start_sec=3, end_sec=8)

    result = exporter.export_package(event_id)

    assert result["status"] == "success"
    assert result["event_id"] == event_id
    assert result["export_id"].startswith("exp-")

    zip_path = Path(result["export_path"])
    assert zip_path.exists()
    assert zip_path.stat().st_size > 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
    assert {"clip.mp4", "snapshot.jpg", "report.json", "report.md"}.issubset(names), names

    # Individual artifacts also exist on disk for direct file:// links.
    out_dir = media_pipeline.media_root() / "exports" / event_id
    assert (out_dir / "clip.mp4").exists()
    assert (out_dir / "snapshot.jpg").exists()
    assert (out_dir / "report.json").exists()
    assert (out_dir / "report.md").exists()

    # Snapshot is a real non-empty JPEG.
    assert (out_dir / "snapshot.jpg").stat().st_size > 0

    # EventExport row reflects success.
    with session_scope() as session:
        row = session.get(EventExport, result["export_id"])
        assert row is not None
        assert row.status == "success"
        assert row.event_id == event_id
        assert row.export_path == str(zip_path)
        assert row.fail_reason == ""

    listings = exporter.list_exports(event_id=event_id)
    assert any(r["id"] == result["export_id"] for r in listings)


def test_export_package_dedups_within_window(sample_video_bytes: bytes) -> None:
    """A second export of the same event reuses the existing package (FR-05)."""
    video_id = media_pipeline.save_upload(
        file_bytes=sample_video_bytes,
        original_filename="dedup.mp4",
        title="dedup smoke",
        owner_id=None,
    )
    event_id = _make_event(video_id, start_sec=2, end_sec=6)

    first = exporter.export_package(event_id)
    assert first["status"] == "success"
    assert first["reused"] is False

    second = exporter.export_package(event_id)
    assert second["status"] == "success"
    assert second["reused"] is True
    assert second["export_id"] == first["export_id"]
    assert second["export_path"] == first["export_path"]

    # force=True bypasses the cache and produces a fresh export id.
    forced = exporter.export_package(event_id, force=True)
    assert forced["reused"] is False
    assert forced["export_id"] != first["export_id"]

    # Only two distinct EventExport rows recorded for this event
    # (the reused call must not write a phantom row).
    rows = exporter.list_exports(event_id=event_id)
    distinct_ids = {r["id"] for r in rows}
    assert distinct_ids == {first["export_id"], forced["export_id"]}


def test_export_batch_exports_multiple_events(sample_video_bytes: bytes) -> None:
    """Controlled batch export handles several events and isolates failures."""
    video_id = media_pipeline.save_upload(
        file_bytes=sample_video_bytes,
        original_filename="batch.mp4",
        title="batch smoke",
        owner_id=None,
    )
    event_a = _make_event(video_id, start_sec=2, end_sec=5)
    event_b = _make_event(video_id, start_sec=6, end_sec=9)

    result = exporter.export_batch([event_a, event_b, "evt-does-not-exist"])

    assert result["total"] == 3
    assert result["succeeded"] == 2
    assert result["failed"] == 1

    by_event = {item["event_id"]: item for item in result["items"]}
    assert by_event[event_a]["status"] == "success"
    assert by_event[event_b]["status"] == "success"
    assert by_event["evt-does-not-exist"]["status"] == "failed"
    assert by_event["evt-does-not-exist"]["fail_reason"]

    # Empty / oversized requests are rejected.
    import pytest as _pytest

    with _pytest.raises(ValueError):
        exporter.export_batch([])
    with _pytest.raises(ValueError):
        exporter.export_batch([f"e{i}" for i in range(exporter.MAX_BATCH_SIZE + 1)])


def test_export_package_failure_records_reason() -> None:
    init_db()
    # Insert a video pointing at a non-existent file, then an event on it.
    video_id = f"vid-bogus{uuid.uuid4().hex[:8]}"
    with session_scope() as session:
        session.add(
            Video(
                id=video_id,
                title="bogus",
                source_path=str(_TEST_SCRATCH / "definitely-missing.mp4"),
                process_status="uploaded",
                duration_sec=10,
            )
        )
    event_id = _make_event(video_id, start_sec=1, end_sec=3)

    with pytest.raises(FileNotFoundError):
        exporter.export_package(event_id)

    rows = exporter.list_exports(event_id=event_id)
    assert rows, "EventExport row should still be recorded on failure"
    assert rows[0]["status"] == "failed"
    assert "FileNotFoundError" in rows[0]["fail_reason"]
