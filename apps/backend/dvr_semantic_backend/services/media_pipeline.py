"""Video upload + ffmpeg preprocessing pipeline.

Implements the media ingest stage of 概要设计 V4:
    upload -> probe metadata -> slice into ~30s segments -> sample keyframes
    -> thumbnail. All artifacts live under ``MEDIA_ROOT`` (defaults to
    ``./var/media``). Rows are persisted into the ``videos``, ``video_segments``
    and ``frame_analysis`` tables via the shared SQLAlchemy session.

Only the service layer lives here; FastAPI routes wire these calls together.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import ffmpeg
from PIL import Image

from ..db import FrameAnalysis, Video, VideoSegment, session_scope

# Bytes used for the demo-grade checksum. Keeps ingestion responsive on large
# dashcam recordings while still detecting accidental corruption / duplicates
# for the course showcase.
_CHECKSUM_PREFIX_BYTES = 4 * 1024 * 1024
_THUMBNAIL_WIDTH = 640


def _ffmpeg_bin() -> str:
    """Resolve the ffmpeg executable (honours FFMPEG_BIN, else PATH)."""
    return os.getenv("FFMPEG_BIN", "").strip() or "ffmpeg"


def _ffprobe_bin() -> str:
    """Resolve the ffprobe executable (honours FFPROBE_BIN, else PATH)."""
    return os.getenv("FFPROBE_BIN", "").strip() or "ffprobe"


def _default_frame_interval() -> int:
    """Frame-sampling cadence in seconds (honours FRAME_INTERVAL_SEC env).

    Lets operators trade vision-model cost against temporal granularity without
    a code change: longer videos use a wider interval to keep the analysed
    frame count (and thus model calls) bounded. Defaults to 3s.
    """
    try:
        return max(1, int(os.getenv("FRAME_INTERVAL_SEC", "3")))
    except (TypeError, ValueError):
        return 3


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def media_root() -> Path:
    """Return the configured media root directory, creating it on demand."""
    raw = os.getenv("MEDIA_ROOT", "").strip() or "./var/media"
    root = Path(raw).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _originals_dir() -> Path:
    p = media_root() / "originals"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _segments_dir(video_id: str) -> Path:
    p = media_root() / "segments" / video_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _frames_dir(video_id: str) -> Path:
    p = media_root() / "frames" / video_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _thumbnails_dir() -> Path:
    p = media_root() / "thumbnails"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _checksum_prefix(path: Path, limit: int = _CHECKSUM_PREFIX_BYTES) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        remaining = limit
        while remaining > 0:
            chunk = fh.read(min(65536, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()


def _safe_ext(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower().lstrip(".")
    if not suffix or any(ch in suffix for ch in (os.sep, "/", "\\", "..")):
        return "mp4"
    # cap to a sensible set; otherwise fall back to mp4
    if len(suffix) > 5 or not suffix.isalnum():
        return "mp4"
    return suffix


def _mark_failed(video_id: str, reason: str) -> None:
    """Best-effort status flip; never raises so callers can re-raise the
    underlying error without masking it."""
    try:
        with session_scope() as session:
            video = session.get(Video, video_id)
            if video is not None:
                video.process_status = "failed"
                video.fail_reason = reason[:2000]
                video.updated_at = datetime.utcnow()
    except Exception:  # pragma: no cover - status update is non-critical
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_upload(
    file_bytes: bytes,
    original_filename: str,
    title: str,
    owner_id: Optional[str],
) -> str:
    """Persist the raw upload to disk and create a ``Video`` row.

    Returns the generated video id. The video starts in ``uploaded`` state;
    follow-up work happens in :func:`run_preprocess`.
    """
    video_id = _new_id("vid")
    ext = _safe_ext(original_filename)
    target = _originals_dir() / f"{video_id}.{ext}"
    target.write_bytes(file_bytes)

    with session_scope() as session:
        session.add(
            Video(
                id=video_id,
                title=title or original_filename or video_id,
                source_path=str(target),
                process_status="uploaded",
                owner_id=owner_id,
            )
        )
    return video_id


def probe_metadata(video_id: str) -> dict:
    """Use ffprobe to populate duration/fps/resolution/checksum for the video.

    The returned dict mirrors the fields written to the ``videos`` row so
    callers can show the metadata immediately without an extra query.
    """
    with session_scope() as session:
        video = session.get(Video, video_id)
        if video is None:
            raise ValueError(f"Unknown video: {video_id}")
        source_path = Path(video.source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source missing: {source_path}")

    probe = ffmpeg.probe(str(source_path), cmd=_ffprobe_bin())
    streams = probe.get("streams", []) or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    fmt = probe.get("format", {}) or {}

    duration_sec = 0
    duration_raw = fmt.get("duration") or (video_stream or {}).get("duration")
    if duration_raw is not None:
        try:
            duration_sec = int(float(duration_raw))
        except (TypeError, ValueError):
            duration_sec = 0

    fps = 0.0
    width = 0
    height = 0
    if video_stream:
        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)
        rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "0/0"
        if "/" in rate:
            num, _, den = rate.partition("/")
            try:
                num_f = float(num)
                den_f = float(den)
                fps = num_f / den_f if den_f else 0.0
            except (TypeError, ValueError):
                fps = 0.0
        else:
            try:
                fps = float(rate)
            except (TypeError, ValueError):
                fps = 0.0

    checksum = _checksum_prefix(source_path)

    with session_scope() as session:
        video = session.get(Video, video_id)
        if video is None:
            raise ValueError(f"Unknown video: {video_id}")
        video.duration_sec = duration_sec
        video.fps = float(fps)
        video.width = width
        video.height = height
        video.checksum = checksum
        video.updated_at = datetime.utcnow()

    return {
        "duration_sec": duration_sec,
        "fps": float(fps),
        "width": width,
        "height": height,
        "checksum": checksum,
    }


def _ensure_mp4_source(source_path: Path, video_id: str) -> Path:
    """If the upload isn't an MP4, transcode it next to the original.

    Returns the path that should be used as input for slicing / sampling.
    """
    if source_path.suffix.lower() == ".mp4":
        return source_path
    mp4_path = source_path.with_name(f"{video_id}.mp4")
    if mp4_path.exists():
        return mp4_path
    (
        ffmpeg
        .input(str(source_path))
        .output(
            str(mp4_path),
            vcodec="libx264",
            acodec="aac",
            movflags="+faststart",
            preset="veryfast",
            pix_fmt="yuv420p",
        )
        .run(cmd=_ffmpeg_bin(), quiet=True, overwrite_output=True)
    )
    return mp4_path


def slice_video(video_id: str, segment_sec: int = 30) -> list[str]:
    """Slice the source into ``segment_sec`` chunks and persist segment rows."""
    if segment_sec <= 0:
        raise ValueError("segment_sec must be positive")

    with session_scope() as session:
        video = session.get(Video, video_id)
        if video is None:
            raise ValueError(f"Unknown video: {video_id}")
        source_path = Path(video.source_path)
        duration_sec = int(video.duration_sec or 0)
    if not source_path.exists():
        raise FileNotFoundError(f"Source missing: {source_path}")

    mp4_source = _ensure_mp4_source(source_path, video_id)
    out_dir = _segments_dir(video_id)
    # Clear any prior run so re-processing yields a clean directory.
    for stale in out_dir.glob("seg_*.mp4"):
        try:
            stale.unlink()
        except OSError:
            pass

    pattern = str(out_dir / "seg_%03d.mp4")
    (
        ffmpeg
        .input(str(mp4_source))
        .output(
            pattern,
            f="segment",
            segment_time=segment_sec,
            reset_timestamps=1,
            c="copy",
        )
        .run(cmd=_ffmpeg_bin(), quiet=True, overwrite_output=True)
    )

    produced = sorted(out_dir.glob("seg_*.mp4"))
    if not produced:
        raise RuntimeError("ffmpeg produced no segments")

    segment_ids: list[str] = []
    with session_scope() as session:
        # Drop any stale segment rows from earlier runs.
        session.query(VideoSegment).filter(VideoSegment.video_id == video_id).delete()
        for idx, seg_path in enumerate(produced):
            start_sec = idx * segment_sec
            if duration_sec > 0 and idx == len(produced) - 1:
                end_sec = duration_sec
            else:
                end_sec = start_sec + segment_sec
            if end_sec <= start_sec:
                end_sec = start_sec + segment_sec
            seg_id = _new_id("seg")
            session.add(
                VideoSegment(
                    id=seg_id,
                    video_id=video_id,
                    segment_index=idx,
                    start_sec=start_sec,
                    end_sec=end_sec,
                    file_path=str(seg_path),
                )
            )
            segment_ids.append(seg_id)
    return segment_ids


def extract_frames(video_id: str, interval_sec: int = 3) -> list[str]:
    """Sample one frame every ``interval_sec`` seconds and queue analysis rows."""
    if interval_sec <= 0:
        raise ValueError("interval_sec must be positive")

    with session_scope() as session:
        video = session.get(Video, video_id)
        if video is None:
            raise ValueError(f"Unknown video: {video_id}")
        source_path = Path(video.source_path)
        duration_sec = int(video.duration_sec or 0)
    if not source_path.exists():
        raise FileNotFoundError(f"Source missing: {source_path}")

    mp4_source = _ensure_mp4_source(source_path, video_id)
    out_dir = _frames_dir(video_id)
    for stale in out_dir.glob("frame_*.jpg"):
        try:
            stale.unlink()
        except OSError:
            pass

    # ffmpeg's fps filter samples at 1/interval Hz; we then rename the
    # numbered outputs to frame_<absolute_seconds>.jpg so downstream
    # consumers can map a file straight back to a timeline offset.
    tmp_pattern = str(out_dir / "_raw_%05d.jpg")
    (
        ffmpeg
        .input(str(mp4_source))
        .output(
            tmp_pattern,
            vf=f"fps=1/{interval_sec}",
            **{"q:v": 3},
        )
        .run(cmd=_ffmpeg_bin(), quiet=True, overwrite_output=True)
    )

    raw_frames = sorted(out_dir.glob("_raw_*.jpg"))
    frame_paths: list[tuple[int, Path]] = []
    for idx, raw in enumerate(raw_frames):
        # ffmpeg's fps filter emits the first frame at t=0; subsequent
        # frames land at the configured interval.
        sec = idx * interval_sec
        if duration_sec > 0 and sec > duration_sec:
            sec = duration_sec
        target = out_dir / f"frame_{sec}.jpg"
        if target.exists():
            target.unlink()
        raw.rename(target)
        frame_paths.append((sec, target))

    frame_ids: list[str] = []
    with session_scope() as session:
        session.query(FrameAnalysis).filter(FrameAnalysis.video_id == video_id).delete()
        for sec, path in frame_paths:
            frame_id = _new_id("frm")
            session.add(
                FrameAnalysis(
                    id=frame_id,
                    video_id=video_id,
                    frame_sec=sec,
                    frame_path=str(path),
                    tags_json=[],
                    frame_summary="",
                    vector_text="",
                    confidence=0.0,
                    analyze_status="pending",
                    model_provider="mock",
                )
            )
            frame_ids.append(frame_id)
    return frame_ids


def generate_thumbnail(video_id: str, at_sec: int = 5) -> str:
    """Grab a single frame at ``at_sec`` and store a 640px-wide JPEG.

    If the clip is shorter than ``at_sec`` we fall back to t=0 so demo
    uploads (a few seconds long) still get a thumbnail.
    """
    with session_scope() as session:
        video = session.get(Video, video_id)
        if video is None:
            raise ValueError(f"Unknown video: {video_id}")
        source_path = Path(video.source_path)
        duration_sec = int(video.duration_sec or 0)
    if not source_path.exists():
        raise FileNotFoundError(f"Source missing: {source_path}")

    mp4_source = _ensure_mp4_source(source_path, video_id)
    seek_to = at_sec
    if duration_sec > 0 and at_sec >= duration_sec:
        seek_to = max(0, duration_sec - 1)
    seek_to = max(0, int(seek_to))

    tmp_path = _thumbnails_dir() / f"{video_id}.raw.jpg"
    final_path = _thumbnails_dir() / f"{video_id}.jpg"
    (
        ffmpeg
        .input(str(mp4_source), ss=seek_to)
        .output(str(tmp_path), vframes=1, **{"q:v": 3})
        .run(cmd=_ffmpeg_bin(), quiet=True, overwrite_output=True)
    )

    with Image.open(tmp_path) as img:
        img = img.convert("RGB")
        if img.width > _THUMBNAIL_WIDTH:
            ratio = _THUMBNAIL_WIDTH / float(img.width)
            new_size = (_THUMBNAIL_WIDTH, max(1, int(img.height * ratio)))
            img = img.resize(new_size, Image.LANCZOS)
        img.save(final_path, format="JPEG", quality=85)
    try:
        tmp_path.unlink()
    except OSError:
        pass

    with session_scope() as session:
        video = session.get(Video, video_id)
        if video is None:
            raise ValueError(f"Unknown video: {video_id}")
        video.thumbnail_path = str(final_path)
        video.updated_at = datetime.utcnow()

    return str(final_path)


def run_preprocess(
    video_id: str,
    segment_sec: int = 30,
    frame_interval_sec: int | None = None,
) -> dict:
    """End-to-end ingest: probe -> slice -> sample frames -> thumbnail.

    The video moves through ``preprocessing`` while ffmpeg runs and lands in
    ``analyzing`` once preprocessing finishes (signalling "ready for the
    vision model" — not a failure). Any exception flips the row to
    ``failed`` with the error string captured in ``fail_reason`` before the
    error propagates to the caller.

    ``frame_interval_sec`` defaults to the ``FRAME_INTERVAL_SEC`` env setting
    (3s) so the same /process endpoint adapts to long recordings via config.
    """
    if frame_interval_sec is None:
        frame_interval_sec = _default_frame_interval()
    try:
        with session_scope() as session:
            video = session.get(Video, video_id)
            if video is None:
                raise ValueError(f"Unknown video: {video_id}")
            video.process_status = "preprocessing"
            video.fail_reason = ""
            video.updated_at = datetime.utcnow()

        meta = probe_metadata(video_id)
        segment_ids = slice_video(video_id, segment_sec=segment_sec)
        frame_ids = extract_frames(video_id, interval_sec=frame_interval_sec)
        generate_thumbnail(video_id)

        with session_scope() as session:
            video = session.get(Video, video_id)
            if video is None:
                raise ValueError(f"Unknown video: {video_id}")
            video.process_status = "analyzing"
            video.updated_at = datetime.utcnow()

        return {
            "segments": len(segment_ids),
            "frames": len(frame_ids),
            "duration_sec": meta.get("duration_sec", 0),
        }
    except Exception as exc:
        _mark_failed(video_id, f"{type(exc).__name__}: {exc}")
        raise


__all__ = [
    "media_root",
    "save_upload",
    "probe_metadata",
    "slice_video",
    "extract_frames",
    "generate_thumbnail",
    "run_preprocess",
]
