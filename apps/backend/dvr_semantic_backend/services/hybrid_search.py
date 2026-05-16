"""Hybrid semantic + keyword search over SemanticEvent rows.

Supports two backends:
- PostgreSQL: uses the ``cosine_similarity(real[], real[])`` stored function
  defined in ``db.init_db()`` for in-database vector scoring.
- SQLite:    computes cosine in Python (numpy) from the embedding column.

Embeddings are computed lazily:
- If ``DVR_SEMANTIC_USE_EMBEDDINGS=1`` and ``sentence_transformers`` can be
  imported, we use the ``paraphrase-multilingual-MiniLM-L12-v2`` model.
- Otherwise we silently fall back to a deterministic 384-d hash-ngram vector
  so unit tests stay reproducible without the heavy ML dependency.
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from typing import Optional

import numpy as np

from sqlalchemy import text

from ..db import IS_SQLITE, SearchQuery, SearchResult, SemanticEvent, session_scope

VECTOR_DIM = 384

KEYWORD_ALIASES: dict[str, tuple[str, ...]] = {
    "scratch": ("剐蹭", "刮蹭", "碰撞", "擦碰"),
    "illegal_parking": ("违停", "停车", "占道"),
    "road_obstacle": ("障碍", "施工", "围挡", "路障"),
    "abnormal_stop": ("异常停车", "急停", "急刹", "鸣笛"),
    "pedestrian_risk": ("行人", "横穿", "鬼探头"),
}

_PUNCT_CHARS = set(" \t\r\n，。、！？!?,.;:；：\"'“”‘’()（）[]【】《》<>")


# ---------------------------------------------------------------------------
# Embedding backends
# ---------------------------------------------------------------------------

_st_model = None  # cached sentence-transformers model (or None if unavailable)
_st_attempted = False


def _try_load_sentence_transformer():
    """Lazy + memoized loader. Returns model instance or None."""
    global _st_model, _st_attempted
    if _st_attempted:
        return _st_model
    _st_attempted = True
    if os.getenv("DVR_SEMANTIC_USE_EMBEDDINGS", "").strip() not in {"1", "true", "True"}:
        return None
    try:  # pragma: no cover - exercised only when extras installed
        from sentence_transformers import SentenceTransformer  # type: ignore

        _st_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    except Exception:
        _st_model = None
    return _st_model


def _hash_token(token: str) -> int:
    """Deterministic 64-bit hash independent of Python's randomized hash seed."""
    digest = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _ngram_tokens(text: str) -> list[str]:
    cleaned = [ch for ch in text if ch not in _PUNCT_CHARS]
    tokens: list[str] = []
    for ch in cleaned:
        if ch.strip():
            tokens.append(ch)
    for i in range(len(cleaned) - 1):
        if cleaned[i].strip() and cleaned[i + 1].strip():
            tokens.append(cleaned[i] + cleaned[i + 1])
    return tokens


def _hash_embed(text: str) -> np.ndarray:
    vec = np.zeros(VECTOR_DIM, dtype=np.float32)
    if not text:
        return vec
    tokens = _ngram_tokens(text.lower())
    for token in tokens:
        h = _hash_token(token)
        idx = h % VECTOR_DIM
        # sign bit to spread mass across both directions
        sign = 1.0 if (h >> 32) & 1 else -1.0
        vec[idx] += sign
    norm = float(np.linalg.norm(vec))
    if norm > 0.0:
        vec /= norm
    return vec


def encode_text(text: str) -> np.ndarray:
    """Return a 384-d L2-normalized float32 vector for ``text``.

    Prefers sentence-transformers when enabled; otherwise hash-ngram fallback.
    """
    model = _try_load_sentence_transformer()
    if model is not None:  # pragma: no cover - heavy optional path
        vec = np.asarray(
            model.encode(text or "", normalize_embeddings=True),
            dtype=np.float32,
        )
        if vec.shape[0] != VECTOR_DIM:  # safety net for unexpected dims
            # truncate or zero-pad to VECTOR_DIM
            resized = np.zeros(VECTOR_DIM, dtype=np.float32)
            n = min(VECTOR_DIM, vec.shape[0])
            resized[:n] = vec[:n]
            norm = float(np.linalg.norm(resized))
            if norm > 0.0:
                resized /= norm
            return resized
        return vec
    return _hash_embed(text or "")


def encode_event(event_id: str) -> np.ndarray:
    """Encode ``event.vector_text`` and cache the result in ``embedding``."""
    with session_scope() as session:
        event = session.get(SemanticEvent, event_id)
        if event is None:
            raise ValueError(f"SemanticEvent not found: {event_id}")
        text = event.vector_text or " ".join(
            filter(None, [event.title or "", event.summary or "", event.event_type or ""])
        )
        vec = encode_text(text)
        event.embedding = [float(x) for x in vec.tolist()]
        return vec


def ensure_embeddings(video_id: Optional[str] = None) -> int:
    """Ensure every (optionally filtered) SemanticEvent has a cached embedding.

    Returns the number of events that were freshly encoded.
    """
    processed = 0
    with session_scope() as session:
        query = session.query(SemanticEvent)
        if video_id is not None:
            query = query.filter(SemanticEvent.video_id == video_id)
        events = query.all()
        targets: list[str] = []
        for ev in events:
            emb = ev.embedding
            if not emb or not isinstance(emb, list) or len(emb) == 0:
                targets.append(ev.id)
    for event_id in targets:
        encode_event(event_id)
        processed += 1
    return processed


# ---------------------------------------------------------------------------
# Keyword scoring
# ---------------------------------------------------------------------------


def _keyword_score(query: str, snapshot: dict) -> tuple[float, list[str]]:
    """Return (score, hit_reasons). ``snapshot`` is a plain dict (session-free)."""
    q = (query or "").lower()
    reasons: list[str] = []
    score = 0.0

    event_type = snapshot.get("event_type") or ""
    aliases = KEYWORD_ALIASES.get(event_type, ())
    for alias in aliases:
        if alias and alias.lower() in q:
            score += 0.4
            reasons.append(f"命中 {event_type} 场景")
            break

    tags = snapshot.get("tags") or []
    for tag in tags:
        tag_s = str(tag)
        if tag_s and tag_s.lower() in q:
            score += 0.2
            reasons.append(f"匹配标签 {tag_s}")
    title = (snapshot.get("title") or "").lower()
    if title and title in q:
        score += 0.2
        reasons.append("命中标题")

    summary = (snapshot.get("summary") or "").lower()
    seen: set[str] = set()
    for raw in q.replace("，", " ").replace(",", " ").split():
        for token in (raw,) + tuple(raw[i : i + 2] for i in range(len(raw) - 1)):
            if token and token not in seen and token in summary:
                seen.add(token)
                score += 0.05
    return score, reasons


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _format_time(sec: int) -> str:
    sec = int(sec or 0)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _answer_text(snapshot: dict, reasons: list[str]) -> str:
    span = f"{_format_time(snapshot.get('start_sec', 0))}-{_format_time(snapshot.get('end_sec', 0))}"
    event_type = snapshot.get("event_type") or ""
    type_cn = {
        "scratch": "剐蹭",
        "illegal_parking": "违停",
        "road_obstacle": "道路障碍",
        "abnormal_stop": "异常停车",
        "pedestrian_risk": "行人风险",
    }.get(event_type, event_type or "事件")
    if reasons:
        head = reasons[0]
    else:
        head = f"语义相似命中 {type_cn} 场景"
    return f"在 {span} {head}"


# ---------------------------------------------------------------------------
# PostgreSQL in-database cosine search (A2: native PG array math)
# ---------------------------------------------------------------------------


def _pg_vector_search(
    session,
    query_vec_list: list[float],
    video_id: Optional[str],
    top_k: int,
) -> list[dict]:
    """Run vector similarity search using PostgreSQL cosine_similarity().

    Returns a list of dicts with keys: id, event_type, title, summary,
    start_sec, end_sec, confidence, tags, thumbnail_path, review_status,
    embedding, vec_score.
    """
    if video_id:
        sql = text("""
            SELECT
                e.id, e.event_type, e.title, e.summary,
                e.start_sec, e.end_sec, e.confidence,
                e.tags_json, e.thumbnail_path, e.review_status, e.embedding,
                cosine_similarity(e.embedding, CAST(:query_vec AS double precision[])) AS vec_score
            FROM semantic_events e
            WHERE e.embedding IS NOT NULL
              AND array_length(e.embedding, 1) > 0
              AND e.video_id = :video_id
            ORDER BY vec_score DESC
            LIMIT :top_k
        """)
        params = {"query_vec": query_vec_list, "video_id": video_id, "top_k": top_k * 3}
    else:
        sql = text("""
            SELECT
                e.id, e.event_type, e.title, e.summary,
                e.start_sec, e.end_sec, e.confidence,
                e.tags_json, e.thumbnail_path, e.review_status, e.embedding,
                cosine_similarity(e.embedding, CAST(:query_vec AS double precision[])) AS vec_score
            FROM semantic_events e
            WHERE e.embedding IS NOT NULL
              AND array_length(e.embedding, 1) > 0
            ORDER BY vec_score DESC
            LIMIT :top_k
        """)
        params = {"query_vec": query_vec_list, "top_k": top_k * 3}

    rows = session.execute(sql, params).fetchall()

    return [
        {
            "id": row.id,
            "event_type": row.event_type,
            "title": row.title,
            "summary": row.summary,
            "start_sec": int(row.start_sec or 0),
            "end_sec": int(row.end_sec or 0),
            "confidence": float(row.confidence or 0.0),
            "tags": list(row.tags_json) if isinstance(row.tags_json, list) else [],
            "thumbnail_path": row.thumbnail_path or "",
            "review_status": row.review_status or "pending",
            "embedding": list(row.embedding) if row.embedding else [],
            "vec_score": float(row.vec_score) if row.vec_score else 0.0,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Hybrid search entry point
# ---------------------------------------------------------------------------


def hybrid_search(
    query: str,
    video_id: Optional[str] = None,
    top_k: int = 10,
    user_id: Optional[str] = None,
    mode: str = "hybrid",
) -> dict:
    started = time.perf_counter()

    # 1. ensure embeddings for the candidate set
    ensure_embeddings(video_id)

    query_vec = encode_text(query or "")
    query_vec_list = [float(x) for x in query_vec.tolist()]

    # 2. vector search: PG in-database or Python fallback
    if not IS_SQLITE:
        # PostgreSQL: use the cosine_similarity stored function
        with session_scope() as session:
            snapshots = _pg_vector_search(session, query_vec_list, video_id, top_k)
        scored: list[dict] = []
        for snap in snapshots:
            vec_score = max(0.0, snap.pop("vec_score", 0.0))
            kw_score, reasons = _keyword_score(query, snap)
            kw_norm = min(1.0, kw_score)
            if mode == "vector":
                final = vec_score
            elif mode == "keyword":
                final = kw_norm
            else:
                final = 0.6 * vec_score + 0.4 * kw_norm
            scored.append(
                {
                    "snap": snap,
                    "final": float(final),
                    "vec": float(vec_score),
                    "kw": float(kw_norm),
                    "reasons": reasons,
                }
            )
    else:
        # SQLite: Python cosine fallback (original code path)
        snapshots: list[dict] = []
        with session_scope() as session:
            q = session.query(SemanticEvent)
            if video_id is not None:
                q = q.filter(SemanticEvent.video_id == video_id)
            for ev in q.all():
                snapshots.append(
                    {
                        "id": ev.id,
                        "event_type": ev.event_type,
                        "title": ev.title,
                        "summary": ev.summary,
                        "start_sec": int(ev.start_sec or 0),
                        "end_sec": int(ev.end_sec or 0),
                        "confidence": float(ev.confidence or 0.0),
                        "tags": list(ev.tags_json) if isinstance(ev.tags_json, list) else [],
                        "thumbnail_path": ev.thumbnail_path or "",
                        "review_status": ev.review_status or "pending",
                        "embedding": list(ev.embedding) if isinstance(ev.embedding, list) else [],
                    }
                )

        scored = []
        for snap in snapshots:
            emb_list = snap.get("embedding") or []
            if emb_list:
                emb_vec = np.asarray(emb_list, dtype=np.float32)
            else:
                emb_vec = np.zeros(VECTOR_DIM, dtype=np.float32)
            vec_score = max(0.0, _cosine(query_vec, emb_vec))
            kw_score, reasons = _keyword_score(query, snap)
            kw_norm = min(1.0, kw_score)
            if mode == "vector":
                final = vec_score
            elif mode == "keyword":
                final = kw_norm
            else:
                final = 0.6 * vec_score + 0.4 * kw_norm
            scored.append(
                {
                    "snap": snap,
                    "final": float(final),
                    "vec": float(vec_score),
                    "kw": float(kw_norm),
                    "reasons": reasons,
                }
            )

    scored.sort(key=lambda item: item["final"], reverse=True)
    kept = [item for item in scored[:top_k] if item["final"] >= 0.15]

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    query_id = f"qry-{uuid.uuid4().hex[:12]}"

    results_payload: list[dict] = []

    with session_scope() as session:
        session.add(
            SearchQuery(
                id=query_id,
                user_id=user_id,
                video_id=video_id,
                query_text=query,
                mode=mode,
                elapsed_ms=elapsed_ms,
                result_count=len(kept),
            )
        )
        for rank, item in enumerate(kept, start=1):
            snap = item["snap"]
            answer = _answer_text(snap, item["reasons"])
            session.add(
                SearchResult(
                    id=f"res-{uuid.uuid4().hex[:12]}",
                    query_id=query_id,
                    event_id=snap["id"],
                    rank_no=rank,
                    similarity_score=float(item["final"]),
                    answer_text=answer,
                )
            )
            results_payload.append(
                {
                    "event_id": snap["id"],
                    "event_type": snap["event_type"],
                    "title": snap["title"],
                    "summary": snap["summary"],
                    "start_sec": snap["start_sec"],
                    "end_sec": snap["end_sec"],
                    "confidence": snap["confidence"],
                    "tags": snap["tags"],
                    "thumbnail_path": snap["thumbnail_path"],
                    "review_status": snap["review_status"],
                    "similarity_score": float(item["final"]),
                    "rank_no": rank,
                    "answer_text": answer,
                }
            )

    return {
        "query_id": query_id,
        "query": query,
        "video_id": video_id,
        "mode": mode,
        "elapsed_ms": elapsed_ms,
        "results": results_payload,
    }
