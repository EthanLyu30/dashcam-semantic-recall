"""Evidence export service.

Materialises an export bundle for a semantic event:
    clip.mp4 + snapshot.jpg + report.json + report.md -> package.zip

Records progress in ``event_exports`` so the desktop UI can show status and
audit trail. All artifacts live under ``media_root()/exports/<event_id>/``.
"""
from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import ffmpeg
from PIL import Image

from ..db import EventExport, SemanticEvent, Video, session_scope
from .media_pipeline import media_root


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _exports_dir(event_id: str) -> Path:
    p = media_root() / "exports" / event_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _load_event_and_video(event_id: str) -> tuple[dict, dict]:
    """Snapshot event + video into plain dicts so callers can use them outside the session."""
    with session_scope() as session:
        event = session.get(SemanticEvent, event_id)
        if event is None:
            raise ValueError(f"Unknown event: {event_id}")
        video = session.get(Video, event.video_id)
        if video is None:
            raise ValueError(f"Event {event_id} references missing video {event.video_id}")
        event_dict = {
            "id": event.id,
            "video_id": event.video_id,
            "event_type": event.event_type,
            "title": event.title,
            "summary": event.summary or "",
            "start_sec": int(event.start_sec or 0),
            "end_sec": int(event.end_sec or 0),
            "confidence": float(event.confidence or 0.0),
            "tags_json": list(event.tags_json or []),
            "thumbnail_path": event.thumbnail_path or "",
            "vector_text": event.vector_text or "",
            "review_status": event.review_status or "",
            "created_at": event.created_at.isoformat() if event.created_at else "",
            "updated_at": event.updated_at.isoformat() if event.updated_at else "",
        }
        video_dict = {
            "id": video.id,
            "title": video.title,
            "source_path": video.source_path,
            "thumbnail_path": video.thumbnail_path or "",
            "duration_sec": int(video.duration_sec or 0),
            "fps": float(video.fps or 0.0),
            "width": int(video.width or 0),
            "height": int(video.height or 0),
            "checksum": video.checksum or "",
            "process_status": video.process_status,
            "created_at": video.created_at.isoformat() if video.created_at else "",
        }
    return event_dict, video_dict


# ---------------------------------------------------------------------------
# Individual export operations
# ---------------------------------------------------------------------------

def export_clip(event_id: str, padding_sec: int = 5) -> Path:
    """ffmpeg-cut a window around the event into ``exports/<event_id>/clip.mp4``."""
    event, video = _load_event_and_video(event_id)
    src = Path(video["source_path"])
    if not src.exists():
        raise FileNotFoundError(f"Source video missing: {src}")

    duration = video["duration_sec"] or 0
    start = max(0, int(event["start_sec"]) - int(padding_sec))
    end_raw = int(event["end_sec"]) + int(padding_sec)
    if duration > 0:
        end = min(duration, end_raw)
    else:
        end = end_raw
    if end <= start:
        end = start + 1

    dst = _exports_dir(event_id) / "clip.mp4"
    if dst.exists():
        dst.unlink()

    # Try stream-copy first (fast, no re-encode). If keyframe alignment makes
    # ffmpeg unhappy we fall back to a real re-encode so we always produce a
    # playable clip.
    try:
        (
            ffmpeg
            .input(str(src), ss=start, to=end)
            .output(str(dst), c="copy")
            .run(quiet=True, overwrite_output=True)
        )
        if not dst.exists() or dst.stat().st_size == 0:
            raise RuntimeError("stream-copy produced empty clip")
    except Exception:
        if dst.exists():
            try:
                dst.unlink()
            except OSError:
                pass
        (
            ffmpeg
            .input(str(src), ss=start, to=end)
            .output(
                str(dst),
                **{"c:v": "libx264", "c:a": "aac"},
                preset="veryfast",
                movflags="+faststart",
                pix_fmt="yuv420p",
            )
            .run(quiet=True, overwrite_output=True)
        )
    return dst


def export_snapshot(event_id: str) -> Path:
    """Grab one frame at the event midpoint and store as JPEG."""
    event, video = _load_event_and_video(event_id)
    src = Path(video["source_path"])
    if not src.exists():
        raise FileNotFoundError(f"Source video missing: {src}")

    start = int(event["start_sec"])
    end = int(event["end_sec"])
    if end < start:
        end = start
    midpoint = (start + end) // 2
    duration = video["duration_sec"] or 0
    if duration > 0 and midpoint >= duration:
        midpoint = max(0, duration - 1)
    midpoint = max(0, midpoint)

    out_dir = _exports_dir(event_id)
    tmp_path = out_dir / "snapshot.raw.jpg"
    final_path = out_dir / "snapshot.jpg"
    for p in (tmp_path, final_path):
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass

    (
        ffmpeg
        .input(str(src), ss=midpoint)
        .output(str(tmp_path), vframes=1, **{"q:v": 3})
        .run(quiet=True, overwrite_output=True)
    )

    if not tmp_path.exists() or tmp_path.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg failed to extract snapshot at t={midpoint}")

    with Image.open(tmp_path) as img:
        img = img.convert("RGB")
        img.save(final_path, format="JPEG", quality=88)
    try:
        tmp_path.unlink()
    except OSError:
        pass
    return final_path


def export_report(event_id: str) -> Path:
    """Write report.json (machine) + report.md (human). Returns json path."""
    event, video = _load_event_and_video(event_id)
    out_dir = _exports_dir(event_id)
    json_path = out_dir / "report.json"
    md_path = out_dir / "report.md"

    generated_at = datetime.utcnow().isoformat() + "Z"
    padding_sec = 5  # mirrors export_clip default; documented in the report

    payload = {
        "schema": "dvr-semantic-event-export/v1",
        "generated_at": generated_at,
        "padding_sec": padding_sec,
        "event": event,
        "source_video": video,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    tags = event.get("tags_json") or []
    tag_str = ", ".join(str(t) for t in tags) if tags else "(无)"
    md_lines = [
        f"# 事件证据报告: {event.get('title', '')}",
        "",
        f"- 事件 ID: `{event['id']}`",
        f"- 类型: {event.get('event_type', '')}",
        f"- 时间区间: {event['start_sec']}s – {event['end_sec']}s",
        f"- 置信度: {event.get('confidence', 0.0):.3f}",
        f"- 复核状态: {event.get('review_status', '')}",
        f"- 标签: {tag_str}",
        "",
        "## 事件摘要",
        "",
        event.get("summary") or "(无摘要)",
        "",
        "## 来源视频",
        "",
        f"- 视频 ID: `{video['id']}`",
        f"- 标题: {video.get('title', '')}",
        f"- 路径: `{video.get('source_path', '')}`",
        f"- 时长: {video.get('duration_sec', 0)}s",
        f"- 分辨率: {video.get('width', 0)}x{video.get('height', 0)} @ {video.get('fps', 0.0):.2f} fps",
        f"- 校验: `{video.get('checksum', '')}`",
        "",
        "## 导出说明",
        "",
        f"- 生成时间 (UTC): {generated_at}",
        f"- 片段前后填充: {padding_sec}s",
        "- 包含文件: clip.mp4 / snapshot.jpg / report.json / report.md",
        "",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return json_path


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def export_package(
    event_id: str,
    operator_id: Optional[str] = None,
    include_video: bool = True,
    include_snapshot: bool = True,
    include_report: bool = True,
) -> dict:
    """End-to-end export: produce artifacts, zip them, persist EventExport row."""
    # Sanity check event exists upfront so we don't write a phantom row.
    _load_event_and_video(event_id)

    export_id = _new_id("exp")
    now = datetime.utcnow()
    with session_scope() as session:
        session.add(
            EventExport(
                id=export_id,
                event_id=event_id,
                operator_id=operator_id,
                export_type="package",
                export_path="",
                status="exporting",
                fail_reason="",
                created_at=now,
                updated_at=now,
            )
        )

    try:
        out_dir = _exports_dir(event_id)
        artifacts: list[Path] = []

        if include_video:
            artifacts.append(export_clip(event_id))
        if include_snapshot:
            artifacts.append(export_snapshot(event_id))
        if include_report:
            json_path = export_report(event_id)
            artifacts.append(json_path)
            md_path = json_path.with_name("report.md")
            if md_path.exists():
                artifacts.append(md_path)

        zip_path = out_dir / "package.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in artifacts:
                if path.exists():
                    zf.write(path, arcname=path.name)

        if not zip_path.exists() or zip_path.stat().st_size == 0:
            raise RuntimeError("Empty package.zip produced")

        absolute_zip = str(zip_path.resolve())
        with session_scope() as session:
            row = session.get(EventExport, export_id)
            if row is not None:
                row.status = "success"
                row.export_path = absolute_zip
                row.fail_reason = ""
                row.updated_at = datetime.utcnow()

        return {
            "export_id": export_id,
            "event_id": event_id,
            "status": "success",
            "export_path": absolute_zip,
        }
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        try:
            with session_scope() as session:
                row = session.get(EventExport, export_id)
                if row is not None:
                    row.status = "failed"
                    row.fail_reason = reason[:2000]
                    row.updated_at = datetime.utcnow()
        except Exception:  # pragma: no cover - status update is best-effort
            pass
        raise


def list_exports(event_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    """Return export rows newest-first as plain dicts."""
    if limit <= 0:
        return []
    with session_scope() as session:
        query = session.query(EventExport)
        if event_id is not None:
            query = query.filter(EventExport.event_id == event_id)
        rows = (
            query.order_by(EventExport.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "event_id": r.event_id,
                "operator_id": r.operator_id,
                "export_type": r.export_type,
                "export_path": r.export_path or "",
                "status": r.status,
                "fail_reason": r.fail_reason or "",
                "created_at": r.created_at.isoformat() if r.created_at else "",
                "updated_at": r.updated_at.isoformat() if r.updated_at else "",
            }
            for r in rows
        ]


__all__ = [
    "export_clip",
    "export_snapshot",
    "export_report",
    "export_package",
    "list_exports",
]
