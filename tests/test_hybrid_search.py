from __future__ import annotations

import importlib
import sys
import uuid
from pathlib import Path

import pytest


@pytest.fixture()
def hybrid_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Spin up an isolated SQLite DB and freshly imported backend modules."""
    db_path = tmp_path / "hybrid_search.db"
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{db_path.as_posix()}")
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

    # Seed a video row so FK PRAGMA stays happy.
    from datetime import datetime

    with db.session_scope() as session:
        session.add(
            db.Video(
                id="vid-test",
                title="测试视频",
                source_path="var/test.mp4",
                duration_sec=600,
                process_status="indexed",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    events_spec = [
        {
            "event_type": "scratch",
            "title": "右后侧剐蹭事件",
            "summary": "右后保险杠出现剐蹭痕迹，疑似碰撞剐蹭。",
            "tags": ["剐蹭", "碰撞"],
            "start": 60,
            "end": 80,
        },
        {
            "event_type": "illegal_parking",
            "title": "路口违停占道",
            "summary": "前方车辆长时间违停，占道严重影响通行。",
            "tags": ["违停", "占道"],
            "start": 120,
            "end": 150,
        },
        {
            "event_type": "road_obstacle",
            "title": "前方道路施工围挡",
            "summary": "前方设置施工围挡与路障，需要减速绕行。",
            "tags": ["施工", "围挡"],
            "start": 200,
            "end": 230,
        },
        {
            "event_type": "normal",
            "title": "普通城市道路驾驶",
            "summary": "平稳行驶，无明显异常事件，仅记录正常通行。",
            "tags": ["正常"],
            "start": 300,
            "end": 360,
        },
    ]

    event_ids = []
    with db.session_scope() as session:
        for spec in events_spec:
            eid = f"evt-{uuid.uuid4().hex[:8]}"
            event_ids.append(eid)
            session.add(
                db.SemanticEvent(
                    id=eid,
                    video_id="vid-test",
                    event_type=spec["event_type"],
                    title=spec["title"],
                    summary=spec["summary"],
                    start_sec=spec["start"],
                    end_sec=spec["end"],
                    confidence=0.7,
                    tags_json=spec["tags"],
                    vector_text=f"{spec['title']} {spec['summary']} {' '.join(spec['tags'])}",
                    embedding_json=[],
                    review_status="pending",
                )
            )

    return db, hybrid, event_ids


def test_ensure_embeddings_populates_vectors(hybrid_env):
    db, hybrid, _ = hybrid_env
    n = hybrid.ensure_embeddings("vid-test")
    assert n == 4
    with db.session_scope() as session:
        events = session.query(db.SemanticEvent).all()
        for ev in events:
            assert isinstance(ev.embedding_json, list)
            assert len(ev.embedding_json) == hybrid.VECTOR_DIM
            assert any(abs(float(x)) > 0 for x in ev.embedding_json)


def test_hybrid_search_finds_illegal_parking(hybrid_env):
    db, hybrid, _ = hybrid_env
    payload = hybrid.hybrid_search("找一下违停", video_id="vid-test", top_k=5)
    assert payload["results"], "should return at least one result"
    assert payload["results"][0]["event_type"] == "illegal_parking"
    assert payload["query_id"].startswith("qry-")
    assert payload["mode"] == "hybrid"
    assert payload["elapsed_ms"] >= 0


def test_hybrid_search_finds_scratch(hybrid_env):
    db, hybrid, _ = hybrid_env
    payload = hybrid.hybrid_search("剐蹭", video_id="vid-test", top_k=5)
    assert payload["results"]
    assert payload["results"][0]["event_type"] == "scratch"
    # answer_text should mention timecode formatted like mm:ss
    assert ":" in payload["results"][0]["answer_text"]


def test_search_query_and_results_persisted(hybrid_env):
    db, hybrid, _ = hybrid_env
    payload = hybrid.hybrid_search(
        "违停", video_id="vid-test", user_id=None, top_k=5
    )
    assert payload["results"]
    with db.session_scope() as session:
        qrow = session.get(db.SearchQuery, payload["query_id"])
        assert qrow is not None
        assert qrow.query_text == "违停"
        assert qrow.result_count == len(payload["results"])
        rrows = (
            session.query(db.SearchResult)
            .filter(db.SearchResult.query_id == payload["query_id"])
            .all()
        )
        assert len(rrows) == len(payload["results"])
        ranks = sorted(r.rank_no for r in rrows)
        assert ranks[0] == 1


def test_vector_mode_runs(hybrid_env):
    _, hybrid, _ = hybrid_env
    payload = hybrid.hybrid_search(
        "违停", video_id="vid-test", top_k=5, mode="vector"
    )
    # should not crash; results may or may not be empty depending on the
    # hash-ngram similarity, but the payload structure must be intact.
    assert payload["mode"] == "vector"
    assert isinstance(payload["results"], list)
    assert payload["query_id"].startswith("qry-")
