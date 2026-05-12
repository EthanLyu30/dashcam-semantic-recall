"""SQLite-backed persistence layer.

Tables follow 概要设计 V4.0 chapter 4. We stay on SQLite for the course demo
(it ships with Python, zero install) and keep the schema close enough to the
PostgreSQL+pgvector design that swapping the engine later is a config change.
Vector similarity is computed in Python rather than via pgvector.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


def _default_db_url() -> str:
    url = os.getenv("DVR_SEMANTIC_DB_URL", "").strip()
    if url:
        return url
    var_dir = Path(__file__).resolve().parents[3] / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{var_dir / 'dvr_semantic.db'}"


DATABASE_URL = _default_db_url()
_engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


@event.listens_for(_engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _record):  # pragma: no cover
    if DATABASE_URL.startswith("sqlite"):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id = Column(String(64), primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="user")  # user | reviewer | admin
    display_name = Column(String(128), default="")
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class Video(Base):
    __tablename__ = "videos"
    id = Column(String(64), primary_key=True)
    title = Column(String(256), nullable=False)
    source_path = Column(String(512), nullable=False)
    thumbnail_path = Column(String(512), default="")
    duration_sec = Column(Integer, default=0, nullable=False)
    fps = Column(Float, default=0.0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    checksum = Column(String(64), default="")
    process_status = Column(String(32), default="uploaded", nullable=False)
    # uploaded | preprocessing | analyzing | indexed | failed | pending_review
    fail_reason = Column(Text, default="")
    owner_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    segments = relationship("VideoSegment", back_populates="video", cascade="all, delete-orphan")
    frames = relationship("FrameAnalysis", back_populates="video", cascade="all, delete-orphan")
    events = relationship("SemanticEvent", back_populates="video", cascade="all, delete-orphan")


class VideoSegment(Base):
    __tablename__ = "video_segments"
    id = Column(String(64), primary_key=True)
    video_id = Column(String(64), ForeignKey("videos.id"), nullable=False, index=True)
    segment_index = Column(Integer, nullable=False)
    start_sec = Column(Integer, nullable=False)
    end_sec = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    video = relationship("Video", back_populates="segments")


class FrameAnalysis(Base):
    __tablename__ = "frame_analysis"
    id = Column(String(64), primary_key=True)
    video_id = Column(String(64), ForeignKey("videos.id"), nullable=False, index=True)
    frame_sec = Column(Integer, nullable=False)
    frame_path = Column(String(512), nullable=False)
    tags_json = Column(JSON, default=list)
    frame_summary = Column(Text, default="")
    vector_text = Column(Text, default="")
    confidence = Column(Float, default=0.0)
    analyze_status = Column(String(32), default="pending")  # pending | done | failed
    model_provider = Column(String(32), default="mock")
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    video = relationship("Video", back_populates="frames")


class SemanticEvent(Base):
    __tablename__ = "semantic_events"
    id = Column(String(64), primary_key=True)
    video_id = Column(String(64), ForeignKey("videos.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    summary = Column(Text, default="")
    start_sec = Column(Integer, nullable=False)
    end_sec = Column(Integer, nullable=False)
    confidence = Column(Float, default=0.0)
    tags_json = Column(JSON, default=list)
    thumbnail_path = Column(String(512), default="")
    vector_text = Column(Text, default="")
    embedding_json = Column(JSON, default=list)  # store list[float] when available
    review_status = Column(String(32), default="pending")
    # pending | reviewing | confirmed | rejected
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    video = relationship("Video", back_populates="events")


class SearchQuery(Base):
    __tablename__ = "search_queries"
    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    video_id = Column(String(64), nullable=True, index=True)
    query_text = Column(Text, nullable=False)
    mode = Column(String(32), default="hybrid")
    elapsed_ms = Column(Integer, default=0)
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class SearchResult(Base):
    __tablename__ = "search_results"
    id = Column(String(64), primary_key=True)
    query_id = Column(String(64), ForeignKey("search_queries.id"), nullable=False, index=True)
    event_id = Column(String(64), ForeignKey("semantic_events.id"), nullable=False)
    rank_no = Column(Integer, default=0)
    similarity_score = Column(Float, default=0.0)
    answer_text = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class EventExport(Base):
    __tablename__ = "event_exports"
    id = Column(String(64), primary_key=True)
    event_id = Column(String(64), ForeignKey("semantic_events.id"), nullable=False, index=True)
    operator_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    export_type = Column(String(32), default="package")  # package | clip | snapshot | report
    export_path = Column(String(512), default="")
    status = Column(String(32), default="queued")  # queued | exporting | success | failed
    fail_reason = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(64), primary_key=True)
    request_id = Column(String(64), index=True)
    user_id = Column(String(64), nullable=True)
    action = Column(String(64), nullable=False)
    target_type = Column(String(32), default="")
    target_id = Column(String(64), default="")
    result_code = Column(String(8), default="00000")
    message = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)


def init_db() -> None:
    Base.metadata.create_all(bind=_engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Session:
    return SessionLocal()


def dumps(obj) -> str:
    """Stable JSON for cases where the column type is plain TEXT instead of JSON."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)
