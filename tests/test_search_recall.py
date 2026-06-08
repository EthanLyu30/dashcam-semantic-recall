"""Semantic-recall quality tests (FR-03 / NFR-04 effectiveness).

Unlike the existing smoke tests, the queries here use *natural language* that
does NOT contain the canonical category noun, plus negative samples (querying
for A must not surface B as the top hit). This is the test the audit flagged as
missing — it actually exercises recall quality rather than substring matching.
"""
from __future__ import annotations

import importlib
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import pytest

EVENTS = [
    ("scratch", "右后侧剐蹭", "右后保险杠有剐蹭痕迹。", ["剐蹭"]),
    ("illegal_parking", "路口违停", "前车长期违停占道。", ["违停"]),
    ("road_obstacle", "道路施工", "前方施工围挡需绕行。", ["施工"]),
    ("abnormal_stop", "前车急停", "前车异常停车并急刹。", ["急停"]),
    ("pedestrian_risk", "行人横穿", "行人突然横穿马路。", ["行人"]),
    ("normal", "正常行驶", "平稳通过，无异常。", ["正常"]),
]


@pytest.fixture()
def search_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{(tmp_path / 'recall.db').as_posix()}")
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
            db.Video(id="vid-r", title="v", source_path="var/r.mp4",
                     duration_sec=600, process_status="indexed",
                     created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
    start = 0
    with db.session_scope() as session:
        for etype, title, summary, tags in EVENTS:
            start += 30
            session.add(
                db.SemanticEvent(
                    id=f"evt-{uuid.uuid4().hex[:8]}", video_id="vid-r",
                    event_type=etype, title=title, summary=summary,
                    start_sec=start, end_sec=start + 10, confidence=0.7,
                    tags_json=tags, vector_text=f"{title} {summary}",
                    embedding=[], review_status="pending",
                )
            )
    return hybrid


# Natural-language queries that DO NOT contain the canonical category noun.
@pytest.mark.parametrize(
    "query,expected",
    [
        ("我的车好像被别的车蹭了一下", "scratch"),
        ("这辆车乱停在路口太久了", "illegal_parking"),
        ("前方路面有东西挡路", "road_obstacle"),
        ("前车突然停车还猛踩刹车", "abnormal_stop"),
        ("突然有人窜出来到车前", "pedestrian_risk"),
    ],
)
def test_natural_language_recall_top1(search_env, query, expected) -> None:
    hybrid = search_env
    payload = hybrid.hybrid_search(query, video_id="vid-r", top_k=5)
    assert payload["results"], f"no results for: {query}"
    assert payload["results"][0]["event_type"] == expected, (
        f"{query!r} -> {[r['event_type'] for r in payload['results']]}"
    )


def test_negative_sample_does_not_cross_match(search_env) -> None:
    hybrid = search_env
    # Asking about a scratch must not rank the pedestrian event first.
    payload = hybrid.hybrid_search("车身被刮花了", video_id="vid-r", top_k=5)
    assert payload["results"][0]["event_type"] == "scratch"
    assert payload["results"][0]["event_type"] != "pedestrian_risk"


def test_search_latency_under_budget(search_env) -> None:
    """NFR-04: hybrid search should return well under the 4s budget."""
    hybrid = search_env
    started = time.perf_counter()
    payload = hybrid.hybrid_search("违停", video_id="vid-r", top_k=10)
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert payload["results"]
    assert elapsed_ms < 4000, f"search took {elapsed_ms:.0f}ms (budget 4000ms)"
    # The route also self-reports elapsed_ms; it must be a sane bounded number.
    assert 0 <= payload["elapsed_ms"] < 4000
