from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def isolated_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Reload the backend modules against an isolated sqlite file."""
    db_path = tmp_path / "auth_audit.db"
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "unit-test-secret-32-bytes-ok-for-jwt-tests")
    monkeypatch.setenv("DVR_SEMANTIC_JWT_TTL_MIN", "30")

    # Drop any cached backend modules so they re-read the env vars on import.
    for name in [
        "dvr_semantic_backend.services.audit",
        "dvr_semantic_backend.services.auth",
        "dvr_semantic_backend.db",
        "dvr_semantic_backend",
    ]:
        sys.modules.pop(name, None)

    db = importlib.import_module("dvr_semantic_backend.db")
    auth = importlib.import_module("dvr_semantic_backend.services.auth")
    audit = importlib.import_module("dvr_semantic_backend.services.audit")
    db.init_db()
    return auth, audit


def test_ensure_seed_users_is_idempotent(isolated_backend):
    auth, _ = isolated_backend
    auth.ensure_seed_users()
    auth.ensure_seed_users()  # second call must not raise nor duplicate

    ctx = auth.authenticate("admin", "admin123")
    assert ctx.role == "admin"
    assert ctx.username == "admin"
    assert ctx.user_id


def test_authenticate_wrong_password_raises(isolated_backend):
    auth, _ = isolated_backend
    auth.ensure_seed_users()
    with pytest.raises(ValueError):
        auth.authenticate("admin", "wrong")


def test_authenticate_unknown_user_raises(isolated_backend):
    auth, _ = isolated_backend
    auth.ensure_seed_users()
    with pytest.raises(ValueError):
        auth.authenticate("ghost", "whatever")


def test_token_roundtrip(isolated_backend):
    auth, _ = isolated_backend
    auth.ensure_seed_users()
    ctx = auth.authenticate("reviewer", "review123")

    token = auth.issue_token(ctx)
    assert isinstance(token, str) and token

    decoded = auth.decode_token(token)
    assert decoded.user_id == ctx.user_id
    assert decoded.username == "reviewer"
    assert decoded.role == "reviewer"


def test_decode_invalid_token_raises(isolated_backend):
    auth, _ = isolated_backend
    with pytest.raises(ValueError):
        auth.decode_token("not-a-real-jwt")


def test_create_user_duplicate_raises(isolated_backend):
    auth, _ = isolated_backend
    auth.create_user("alice", "pw12345", role="user")
    with pytest.raises(ValueError):
        auth.create_user("alice", "pw12345", role="user")


def test_log_action_and_recent_logs(isolated_backend):
    auth, audit = isolated_backend
    auth.ensure_seed_users()
    ctx = auth.authenticate("demo", "demo123")

    audit.log_action(
        request_id="req-001",
        user_id=ctx.user_id,
        action="login",
        target_type="user",
        target_id=ctx.user_id,
        result_code="00000",
        message="ok",
    )

    rows = audit.recent_logs(limit=1)
    assert len(rows) == 1
    row = rows[0]
    assert row["request_id"] == "req-001"
    assert row["action"] == "login"
    assert row["user_id"] == ctx.user_id
    assert row["result_code"] == "00000"
    assert row["created_at"]


def test_log_action_never_raises(isolated_backend):
    _, audit = isolated_backend
    # Calling with weird values must not bubble up an exception.
    audit.log_action(
        request_id="",
        user_id=None,
        action="noop",
    )
    rows = audit.recent_logs(limit=5)
    assert any(r["action"] == "noop" for r in rows)
