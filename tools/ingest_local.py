"""Ingest a local video file end-to-end through the real pipeline.

A thin operator/dev CLI that mirrors what the ``POST /api/videos`` +
``/process`` endpoints do, but straight against the service layer — handy for
seeding the database with a real recording (no HTTP/auth round-trip):

    python tools/ingest_local.py var/real_dashcam_long.mp4 --title "城市道路实拍 2 分钟"

It loads ``.env`` first (model keys, DB url, ffmpeg paths, FRAME_INTERVAL_SEC),
registers the file as a ``Video``, runs preprocess (probe → slice → sample
frames → thumbnail) and the full vision analysis (per-frame model labels →
aggregated ``SemanticEvent`` rows), then prints a JSON summary of the events.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Load .env BEFORE importing backend modules so db.py's import-time
# load_dotenv(override=False) doesn't clobber our explicit values.
try:
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(_repo_root / ".env", override=False)
except Exception:  # pragma: no cover - dotenv optional
    _repo_root = Path(__file__).resolve().parents[1]

# Make the backend package importable when run from the repo root.
sys.path.insert(0, str(_repo_root / "apps" / "backend"))

from dvr_semantic_backend.db import SemanticEvent, session_scope  # noqa: E402
from dvr_semantic_backend.services import (  # noqa: E402
    event_aggregator,
    media_pipeline,
)


def ingest(path: Path, title: str, owner_id: str | None) -> dict:
    if not path.exists():
        raise SystemExit(f"file not found: {path}")

    print(f"[1/3] 注册视频: {path.name} ({path.stat().st_size/1_048_576:.1f} MB)")
    video_id = media_pipeline.save_upload(
        file_bytes=path.read_bytes(),
        original_filename=path.name,
        title=title or path.stem,
        owner_id=owner_id,
    )
    print(f"      video_id = {video_id}")

    print("[2/3] 预处理（探测 → 切片 → 抽帧 → 缩略图）…")
    pre = media_pipeline.run_preprocess(video_id)
    print(f"      segments={pre.get('segments')} frames={pre.get('frames')} "
          f"duration={pre.get('duration_sec')}s")

    print("[3/3] 视觉分析（逐帧大模型标注 → 聚合事件）… 这一步会真实调用模型")
    stats = event_aggregator.run_full_analysis(video_id)
    print(f"      frames_analyzed={stats.get('frames_analyzed')} "
          f"events_created={stats.get('events_created')}")

    with session_scope() as session:
        rows = (
            session.query(SemanticEvent)
            .filter(SemanticEvent.video_id == video_id)
            .order_by(SemanticEvent.start_sec.asc())
            .all()
        )
        events = [
            {
                "id": r.id,
                "type": r.event_type,
                "title": r.title,
                "start": r.start_sec,
                "end": r.end_sec,
                "confidence": round(float(r.confidence or 0.0), 3),
                "summary": (r.summary or "")[:120],
            }
            for r in rows
        ]

    return {"video_id": video_id, "preprocess": pre, "analysis": stats, "events": events}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a local video end-to-end.")
    parser.add_argument("path", type=Path, help="path to the video file")
    parser.add_argument("--title", default="", help="display title")
    parser.add_argument("--owner", default=None, help="owner user id (optional)")
    args = parser.parse_args()

    result = ingest(args.path, args.title, args.owner)
    print("\n=== 事件汇总 ===")
    print(json.dumps(result["events"], ensure_ascii=False, indent=2))
    print(f"\nvideo_id={result['video_id']} "
          f"events={len(result['events'])}")


if __name__ == "__main__":
    main()
