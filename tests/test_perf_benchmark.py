"""Performance benchmark for hybrid search at scale (SRS NFR-04: 检索 ≤ 4s).

Seeds a few hundred events and asserts the SQLite/numpy search path stays well
within the latency budget. This is the reproducible benchmark the audit noted
was missing; for true 2h/4K preprocessing and 50-concurrent numbers a load test
against a real corpus is still required (tracked in docs/requirements-trace.md).
"""
from __future__ import annotations

import importlib
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import pytest

_CORPUS_SIZE = 300
_BUDGET_MS = 4000
_TYPES = ["scratch", "illegal_parking", "road_obstacle", "abnormal_stop", "pedestrian_risk", "normal"]


@pytest.fixture()
def big_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{(tmp_path / 'perf.db').as_posix()}")
    monkeypatch.delenv("DVR_SEMANTIC_USE_EMBEDDINGS", raising=False)
    for name in [
        "dvr_semantic_backend.services.hybrid_search",
        "dvr_semantic_backend.db",
        "dvr_semantic_backend.services",
        "dvr_semantic_backend",
    ]:
        sys.modules.pop(name, None)
    db = importlib.import_module("dvr_semantic_backend.db")
    hybrid = importlib.import_module("dvr_semantic_backend.services.hybrid_search")
    db.init_db()
    with db.session_scope() as session:
        session.add(
            db.Video(id="vid-perf", title="perf", source_path="var/p.mp4",
                     duration_sec=7200, process_status="indexed",
                     created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
    with db.session_scope() as session:
        for i in range(_CORPUS_SIZE):
            etype = _TYPES[i % len(_TYPES)]
            session.add(
                db.SemanticEvent(
                    id=f"evt-{uuid.uuid4().hex[:10]}", video_id="vid-perf",
                    event_type=etype, title=f"{etype}-{i}",
                    summary=f"事件 {i} 描述 {etype} 场景。",
                    start_sec=i * 10, end_sec=i * 10 + 5, confidence=0.6,
                    tags_json=[etype], vector_text=f"{etype} {i}",
                    embedding=[], review_status="pending",
                )
            )
    return hybrid


def test_search_over_300_events_within_budget(big_corpus) -> None:
    hybrid = big_corpus
    # Warm the embedding cache once (mirrors a steady-state deployment).
    hybrid.ensure_embeddings("vid-perf")

    started = time.perf_counter()
    payload = hybrid.hybrid_search("找一下违停", video_id="vid-perf", top_k=10)
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert payload["results"]
    assert payload["results"][0]["event_type"] == "illegal_parking"
    assert elapsed_ms < _BUDGET_MS, (
        f"search over {_CORPUS_SIZE} events took {elapsed_ms:.0f}ms (budget {_BUDGET_MS}ms)"
    )
